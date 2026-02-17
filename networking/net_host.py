# networking/net_host.py
"""
Host (P2P server) - one player hosts, others connect via IP.
The host is authoritative over enemy spawning and wave progression.
Supports both direct P2P and relay mode.
"""

import socket
import threading
import time
import json
from networking.net_common import *


class GameHost:
    def __init__(self, port=DEFAULT_PORT, max_players=4):
        self.port = port
        self.max_players = max_players
        self.server_socket = None
        self.clients = {}  # {player_id: {"socket": sock, "buffer": b"", "name": "", "state": {}}}
        self.next_id = 1  # Host is always player 0
        self.running = False
        self.lock = threading.Lock()
        self.message_queue = []  # Messages for the host game to process
        self.host_player_id = 0
        self.lobby_name = "Game"
        self.password = ""  # Empty = no password
        # Relay mode
        self._relay_mode = False
        self._relay_sock = None
        self._relay_code = None

    def start(self):
        """Start listening for connections (direct P2P mode)."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(self.max_players)
        self.server_socket.settimeout(1.0)
        self.running = True

        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

        # Start UDP broadcast beacon for server discovery
        self._beacon_thread = threading.Thread(target=self._beacon_loop, daemon=True)
        self._beacon_thread.start()

        local_ip = get_local_ip()
        print(f"[Host] Server started on {local_ip}:{self.port}")
        return local_ip

    def start_relay(self, relay_sock, room_code):
        """Start in relay mode — use an existing relay socket instead of listening."""
        self._relay_mode = True
        self._relay_sock = relay_sock
        self._relay_code = room_code
        self.running = True

        # In relay mode, data from ALL clients arrives on one socket.
        # The relay server handles multiplexing — each client gets its own
        # TCP connection to the relay, and the relay forwards to us.
        # But from our side, it looks like one connection carrying all traffic.
        # We treat the relay socket as a single "virtual client" pipe.
        # Actually: the relay broadcasts our data to all clients and
        # forwards each client's data to us. So we receive interleaved
        # data from multiple clients on one socket.
        # We still need to accept new clients — the relay will send
        # the game protocol handshake data from each client through us.
        # So we just treat the relay socket like we have one multiplexed client.

        self.accept_thread = threading.Thread(target=self._relay_receive_loop, daemon=True)
        self.accept_thread.start()

        print(f"[Host] Relay mode started — room code: {room_code}")
        return room_code

    def _relay_receive_loop(self):
        """Receive data from the relay socket (all clients multiplexed).

        In relay mode, ALL client data arrives on one socket. The relay server
        forwards each client's TCP stream to us merged together. Since our game
        protocol is length-prefixed, messages are self-delimiting and we can
        decode them from the combined stream.

        We treat all relay clients as a single virtual client (relay_id=1).
        The game protocol already handles multi-client state via player_id
        fields in messages.
        """
        # Wait briefly for a client to actually connect before creating the virtual client
        # The relay forwards client data as soon as they join
        buf = b""
        self._relay_sock.settimeout(1.0)
        relay_id = None

        while self.running:
            try:
                data = self._relay_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                buf += data
                messages, buf = decode_messages(buf)

                for msg in messages:
                    # First message from a client through relay — create virtual client
                    if relay_id is None:
                        relay_id = self.next_id
                        self.next_id += 1
                        with self.lock:
                            self.clients[relay_id] = {
                                "socket": self._relay_sock,
                                "buffer": b"",
                                "name": f"Player {relay_id}",
                                "username": f"Player{relay_id}",
                                "state": {},
                                "addr": ("relay", 0),
                                "_is_relay": True,
                            }
                        # Send handshake back through relay
                        handshake = encode_message(MSG_HANDSHAKE, {
                            "your_id": relay_id,
                            "host_id": self.host_player_id,
                            "players": self._get_player_list(),
                        })
                        try:
                            self._relay_sock.sendall(handshake)
                        except:
                            pass
                        print(f"[Host] Relay client {relay_id} connected")

                    msg["_from"] = relay_id
                    self._handle_message(msg, relay_id)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Host] Relay receive error: {e}")
                break

        print("[Host] Relay connection lost")
        if relay_id is not None:
            self._disconnect_player(relay_id)

    def _beacon_loop(self):
        """Broadcast server info via UDP for LAN discovery."""
        if self._relay_mode:
            return  # No LAN beacon in relay mode
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1.0)
        except Exception as e:
            print(f"[Host] Beacon setup failed: {e}")
            return
        while self.running:
            try:
                with self.lock:
                    pc = 1 + len(self.clients)
                info = json.dumps({
                    "name": self.lobby_name,
                    "port": self.port,
                    "players": pc,
                    "max": self.max_players,
                    "has_password": bool(self.password),
                    "ip": get_local_ip(),
                }).encode("utf-8")
                sock.sendto(info, ("<broadcast>", BROADCAST_PORT))
            except Exception:
                pass
            time.sleep(1.5)
        sock.close()

    def stop(self):
        """Shut down the server."""
        self.running = False
        self.broadcast(MSG_DISCONNECT, {"reason": "Host closed"})
        with self.lock:
            for pid, client in self.clients.items():
                try:
                    client["socket"].close()
                except Exception:
                    pass
            self.clients.clear()
        if self.server_socket:
            self.server_socket.close()
        print("[Host] Server stopped.")

    def _accept_loop(self):
        """Accept incoming connections."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                conn.settimeout(0.5)
                player_id = self.next_id
                self.next_id += 1

                with self.lock:
                    self.clients[player_id] = {
                        "socket": conn,
                        "buffer": b"",
                        "name": f"Player {player_id}",
                        "username": f"Player{player_id}",
                        "state": {},
                        "addr": addr,
                    }

                # Send handshake
                handshake = encode_message(MSG_HANDSHAKE, {
                    "your_id": player_id,
                    "host_id": self.host_player_id,
                    "players": self._get_player_list(),
                })
                conn.sendall(handshake)

                # Notify others
                self.broadcast(MSG_CHAT, {
                    "message": f"Player {player_id} joined from {addr[0]}"
                }, exclude=player_id)

                # Start receive thread
                t = threading.Thread(target=self._receive_loop, args=(player_id,), daemon=True)
                t.start()

                print(f"[Host] Player {player_id} connected from {addr}")

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Host] Accept error: {e}")

    def _receive_loop(self, player_id):
        """Receive messages from a specific client."""
        while self.running:
            try:
                with self.lock:
                    if player_id not in self.clients:
                        break
                    sock = self.clients[player_id]["socket"]

                data = sock.recv(BUFFER_SIZE)
                if not data:
                    self._disconnect_player(player_id)
                    break

                with self.lock:
                    self.clients[player_id]["buffer"] += data
                    messages, remaining = decode_messages(self.clients[player_id]["buffer"])
                    self.clients[player_id]["buffer"] = remaining

                for msg in messages:
                    msg["_from"] = player_id
                    self._handle_message(msg, player_id)

            except socket.timeout:
                continue
            except Exception as e:
                self._disconnect_player(player_id)
                break

    def _handle_message(self, msg, from_id):
        """Process a message from a client."""
        msg_type = msg.get("type", "")
        data = msg.get("data", {})

        if msg_type == MSG_PLAYER_STATE:
            # Relay player state to all others
            data["player_id"] = from_id
            self.broadcast(MSG_PLAYER_STATE, data, exclude=from_id)

            # Also queue for host's game
            with self.lock:
                if from_id in self.clients:
                    self.clients[from_id]["state"] = data
                self.message_queue.append(msg)

        elif msg_type == MSG_BULLET_FIRE:
            data["player_id"] = from_id
            self.broadcast(MSG_BULLET_FIRE, data, exclude=from_id)
            with self.lock:
                self.message_queue.append(msg)

        elif msg_type == MSG_PING:
            self.send_to(from_id, MSG_PONG, {"time": data.get("time", 0)})

        elif msg_type == MSG_USERNAME:
            # Store and broadcast username to all others
            username = data.get("username", f"Player{from_id}")
            with self.lock:
                if from_id in self.clients:
                    self.clients[from_id]["username"] = username
            self.broadcast(MSG_USERNAME, {"player_id": from_id, "username": username}, exclude=from_id)

        elif msg_type == MSG_DISCONNECT:
            self._disconnect_player(from_id)

        else:
            # Generic relay + queue
            data["player_id"] = from_id
            self.broadcast(msg_type, data, exclude=from_id)
            with self.lock:
                self.message_queue.append(msg)

    def _disconnect_player(self, player_id):
        """Handle a player disconnecting."""
        with self.lock:
            if player_id in self.clients:
                try:
                    self.clients[player_id]["socket"].close()
                except Exception:
                    pass
                del self.clients[player_id]
                print(f"[Host] Player {player_id} disconnected.")

        self.broadcast(MSG_DISCONNECT, {"player_id": player_id})
        with self.lock:
            self.message_queue.append({
                "type": MSG_DISCONNECT,
                "data": {"player_id": player_id}
            })

    def _get_player_list(self):
        """Get list of connected player IDs."""
        with self.lock:
            return [self.host_player_id] + list(self.clients.keys())

    def broadcast(self, msg_type, data=None, exclude=None):
        """Send a message to all connected clients (non-blocking)."""
        raw = encode_message(msg_type, data)
        with self.lock:
            for pid, client in list(self.clients.items()):
                if pid == exclude:
                    continue
                try:
                    client["socket"].setblocking(False)
                    client["socket"].send(raw)
                except BlockingIOError:
                    # Queue for later — append to client buffer
                    if "_send_buf" not in client:
                        client["_send_buf"] = bytearray()
                    client["_send_buf"].extend(raw)
                except Exception:
                    pass
                finally:
                    try:
                        client["socket"].setblocking(True)
                        client["socket"].settimeout(0.5)
                    except Exception:
                        pass

    def send_to(self, player_id, msg_type, data=None):
        """Send a message to a specific client."""
        raw = encode_message(msg_type, data)
        with self.lock:
            if player_id in self.clients:
                try:
                    self.clients[player_id]["socket"].sendall(raw)
                except Exception:
                    pass

    def get_messages(self):
        """Get and clear queued messages for the host game loop."""
        with self.lock:
            msgs = list(self.message_queue)
            self.message_queue.clear()
        return msgs

    def get_player_count(self):
        with self.lock:
            return 1 + len(self.clients)  # +1 for host

    def get_remote_states(self):
        """Get the latest state of all remote players."""
        with self.lock:
            return {pid: c["state"] for pid, c in self.clients.items() if c["state"]}

    def get_usernames(self):
        """Get mapping of player_id -> username for all clients."""
        with self.lock:
            return {pid: c.get("username", f"Player{pid}") for pid, c in self.clients.items()}