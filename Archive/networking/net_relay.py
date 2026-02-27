# networking/net_relay.py
"""
Relay connection helpers.
Connects to the relay server, does the handshake (create/join room),
then returns a socket that behaves identically to a direct P2P connection.

The game's GameHost and GameClient don't need to change —
they just use the relay socket instead of a direct socket.
"""

import socket
import struct
import json

try:
    from updater.version import RELAY_HOST, RELAY_PORT
except ImportError:
    RELAY_HOST = "updates.r3dwolfie.com"
    RELAY_PORT = 27020


def _send_msg(sock, msg_type, data=None):
    payload = json.dumps({"type": msg_type, "data": data or {}}).encode("utf-8")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def _recv_msg(sock, timeout=10):
    sock.settimeout(timeout)
    raw_len = b""
    while len(raw_len) < 4:
        chunk = sock.recv(4 - len(raw_len))
        if not chunk:
            return None
        raw_len += chunk
    msg_len = struct.unpack("!I", raw_len)[0]
    if msg_len > 65536:
        return None
    raw = b""
    while len(raw) < msg_len:
        chunk = sock.recv(msg_len - len(raw))
        if not chunk:
            return None
        raw += chunk
    return json.loads(raw.decode("utf-8"))


def create_relay_room(name="Game", password="", max_players=4, host=None, port=None):
    """
    Connect to the relay server and create a room.

    Returns (socket, room_code) on success.
    The returned socket is ready for GameHost to accept_loop on —
    but since the relay handles multiplexing, we use a different approach:
    see RelayHostAdapter.

    Returns (None, error_msg) on failure.
    """
    relay_host = host or RELAY_HOST
    relay_port = port or RELAY_PORT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((relay_host, relay_port))

        _send_msg(sock, "create_room", {
            "name": name,
            "password": password,
            "max_players": max_players,
        })

        resp = _recv_msg(sock, timeout=10)
        if not resp:
            sock.close()
            return None, "No response from relay"

        if resp.get("type") == "room_created":
            code = resp["data"]["code"]
            return sock, code
        else:
            err = resp.get("data", {}).get("message", "Unknown error")
            sock.close()
            return None, err

    except Exception as e:
        return None, str(e)


def join_relay_room(room_code, password="", host=None, port=None):
    """
    Connect to the relay server and join an existing room.

    Returns socket on success (ready for GameClient to use as its connection).
    Returns (None, error_msg) on failure.
    """
    relay_host = host or RELAY_HOST
    relay_port = port or RELAY_PORT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((relay_host, relay_port))

        _send_msg(sock, "join_room", {
            "code": room_code.upper().strip(),
            "password": password,
        })

        resp = _recv_msg(sock, timeout=10)
        if not resp:
            sock.close()
            return None, "No response from relay"

        if resp.get("type") == "joined":
            return sock, None
        else:
            err = resp.get("data", {}).get("message", "Unknown error")
            sock.close()
            return None, err

    except Exception as e:
        return None, str(e)