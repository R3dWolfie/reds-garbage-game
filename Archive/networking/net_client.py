# networking/net_client.py
"""
Client that connects to a host via IP address.
"""

import socket
import threading
import time
from networking.net_common import *


class GameClient:
    def __init__(self):
        self.socket = None
        self.buffer = b""
        self.running = False
        self.connected = False
        self.my_id = -1
        self.host_id = 0
        self.players = []
        self.lock = threading.Lock()
        self.message_queue = []
        self.remote_states = {}
        self.remote_usernames = {}  # {player_id: username}

    def connect(self, host_ip, port=DEFAULT_PORT, timeout=10):
        """Connect to a host. Returns True on success."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((host_ip, port))
            self.socket.settimeout(0.5)
            configure_socket(self.socket)  # TCP_NODELAY + buffer sizes
            self.running = True
            self.connected = True

            # Start receive thread
            self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.recv_thread.start()

            # Wait for handshake
            start = time.time()
            while self.my_id == -1 and time.time() - start < timeout:
                time.sleep(0.1)

            if self.my_id == -1:
                self.disconnect()
                return False

            print(f"[Client] Connected as Player {self.my_id}")
            return True

        except Exception as e:
            print(f"[Client] Connection failed: {e}")
            self.connected = False
            return False

    def connect_relay(self, relay_sock, username=None):
        """Connect using an already-established relay socket.
        The relay handshake is already done — socket is ready for game protocol."""
        try:
            self.socket = relay_sock
            self.socket.settimeout(0.5)
            configure_socket(self.socket)  # TCP_NODELAY
            self.running = True
            self.connected = True

            # Start receive thread
            self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.recv_thread.start()

            # Send a message to the host through relay so it knows we're here
            # The host creates our virtual client slot when it receives this
            if username:
                self.send_username(username)
            else:
                # Send a ping/hello so the host sees us
                self.send_username("Player")

            # Wait for handshake from host (through relay)
            start = time.time()
            while self.my_id == -1 and time.time() - start < 10:
                time.sleep(0.1)

            if self.my_id == -1:
                self.disconnect()
                return False

            print(f"[Client] Connected via relay as Player {self.my_id}")
            return True

        except Exception as e:
            print(f"[Client] Relay connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from the host."""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.sendall(encode_message(MSG_DISCONNECT, {}))
                self.socket.close()
            except Exception:
                pass
        print("[Client] Disconnected.")

    def _receive_loop(self):
        """Receive messages from the host."""
        while self.running:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                if not data:
                    print("[Client] recv returned empty (host closed connection)")
                    self.connected = False
                    break

                self.buffer += data
                messages, self.buffer = decode_messages(self.buffer)

                for msg in messages:
                    self._handle_message(msg)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Client] Receive error: {type(e).__name__}: {e}")
                    self.connected = False
                break

    def _handle_message(self, msg):
        """Process a message from the host."""
        msg_type = msg.get("type", "")
        data = msg.get("data", {})

        if msg_type == MSG_HANDSHAKE:
            self.my_id = data.get("your_id", -1)
            self.host_id = data.get("host_id", 0)
            self.players = data.get("players", [])
            print(f"[Client] Handshake: I am Player {self.my_id}")

        elif msg_type == MSG_PLAYER_STATE:
            pid = data.get("player_id", -1)
            with self.lock:
                self.remote_states[pid] = data

        elif msg_type == MSG_USERNAME:
            pid = data.get("player_id", -1)
            username = data.get("username", f"Player{pid}")
            with self.lock:
                self.remote_usernames[pid] = username

        elif msg_type == MSG_DISCONNECT:
            pid = data.get("player_id", -1)
            if pid == -1:
                # Host disconnected
                self.connected = False
            else:
                with self.lock:
                    self.remote_states.pop(pid, None)

        # Queue everything for the game loop
        with self.lock:
            self.message_queue.append(msg)

    def send(self, msg_type, data=None):
        """Queue a message to send to the host (non-blocking)."""
        if not self.connected:
            return
        try:
            raw = encode_message(msg_type, data)
            with self.lock:
                if not hasattr(self, '_send_queue'):
                    self._send_queue = bytearray()
                self._send_queue.extend(raw)
            self._flush_send()
        except Exception as e:
            print(f"[Client] Send error: {e}")
            self.connected = False

    def _flush_send(self):
        """Try to send queued data without blocking."""
        with self.lock:
            if not hasattr(self, '_send_queue') or not self._send_queue:
                return
            try:
                self.socket.setblocking(False)
                sent = self.socket.send(bytes(self._send_queue))
                if sent > 0:
                    self._send_queue = self._send_queue[sent:]
            except BlockingIOError:
                pass  # Would block — will retry next frame
            except Exception as e:
                print(f"[Client] Flush error: {e}")
                self.connected = False
            finally:
                try:
                    self.socket.setblocking(True)
                    self.socket.settimeout(0.5)
                except Exception:
                    pass

    def send_username(self, username):
        """Send our chosen username to the host."""
        self.send(MSG_USERNAME, {"username": username})

    def send_player_state(self, x, y, health, class_key, level, max_health=100, equipped_hat=None, is_dead=False, magnet_r=0):
        """Send our current state to the host (called every frame or every few frames)."""
        data = {
            "x": x,
            "y": y,
            "health": health,
            "max_health": max_health,
            "class": class_key,
            "level": level,
            "equipped_hat": equipped_hat,
            "is_dead": is_dead,
        }
        if magnet_r > 0:
            data["magnet_r"] = magnet_r
        self.send(MSG_PLAYER_STATE, data)

    def get_messages(self):
        """Get and clear queued messages."""
        with self.lock:
            msgs = list(self.message_queue)
            self.message_queue.clear()
        return msgs

    def get_remote_states(self):
        """Get latest states of all remote players."""
        with self.lock:
            return dict(self.remote_states)

    def get_remote_usernames(self):
        """Get mapping of player_id -> username."""
        with self.lock:
            return dict(self.remote_usernames)