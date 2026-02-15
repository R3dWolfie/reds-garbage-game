# networking/net_host.py
"""
Host (P2P server) - one player hosts, others connect via IP.
The host is authoritative over enemy spawning and wave progression.
"""

import socket
import threading
import time
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

    def start(self):
        """Start listening for connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(self.max_players)
        self.server_socket.settimeout(1.0)
        self.running = True

        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

        local_ip = get_local_ip()
        print(f"[Host] Server started on {local_ip}:{self.port}")
        return local_ip

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
        """Send a message to all connected clients."""
        raw = encode_message(msg_type, data)
        with self.lock:
            for pid, client in list(self.clients.items()):
                if pid == exclude:
                    continue
                try:
                    client["socket"].sendall(raw)
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
