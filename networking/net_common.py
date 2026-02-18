# networking/net_common.py
"""
Shared protocol definitions for P2P multiplayer.
Uses raw TCP sockets with JSON messages.
Optimized for low-latency game state sync.
"""

import json
import struct
import socket

DEFAULT_PORT = 27015
BROADCAST_PORT = 27016  # UDP broadcast for server discovery
BUFFER_SIZE = 8192  # Larger buffer to reduce recv() calls

# Message types
MSG_HANDSHAKE = "handshake"
MSG_PLAYER_STATE = "player_state"
MSG_ENEMY_SPAWN = "enemy_spawn"
MSG_ENEMY_UPDATE = "enemy_update"
MSG_ENEMY_KILL = "enemy_kill"
MSG_BULLET_FIRE = "bullet_fire"
MSG_DAMAGE = "damage"
MSG_LEVEL_UP = "level_up"
MSG_WAVE_START = "wave_start"
MSG_GEM_SPAWN = "gem_spawn"
MSG_ORB_SPAWN = "orb_spawn"
MSG_GEM_COLLECT = "gem_collect"
MSG_UPGRADE_PAUSE = "upgrade_pause"
MSG_UPGRADE_RESUME = "upgrade_resume"
MSG_PLAYER_DIED = "player_died"
MSG_CHAT = "chat"
MSG_DISCONNECT = "disconnect"
MSG_PING = "ping"
MSG_PONG = "pong"
MSG_GAME_START = "game_start"
MSG_USERNAME = "username"
MSG_ENEMY_DEAD = "enemy_dead"
MSG_WAVE_COMPLETE = "wave_complete"
MSG_PARTY_LEVEL_UP = "party_level_up"
MSG_UPGRADE_DONE = "upgrade_done"
MSG_GOLD_SYNC = "gold_sync"
MSG_HAT_DROP = "hat_drop"
MSG_ORB_PICKUP = "orb_pickup"
MSG_SHAKE = "shake"
MSG_REVIVE = "revive"

# Short type codes for bandwidth — map full names to 1-2 char codes
_TYPE_TO_CODE = {
    MSG_PLAYER_STATE: "ps",
    MSG_ENEMY_UPDATE: "eu",
    MSG_BULLET_FIRE: "bf",
    MSG_ENEMY_SPAWN: "es",
    MSG_ENEMY_DEAD: "ed",
    MSG_GEM_SPAWN: "gs",
    MSG_GEM_COLLECT: "gc",
    MSG_WAVE_START: "ws",
    MSG_WAVE_COMPLETE: "wc",
    MSG_PARTY_LEVEL_UP: "pl",
    MSG_UPGRADE_PAUSE: "up",
    MSG_UPGRADE_RESUME: "ur",
    MSG_UPGRADE_DONE: "ud",
    MSG_ORB_SPAWN: "os",
    MSG_ORB_PICKUP: "op",
    MSG_DAMAGE: "dm",
    MSG_SHAKE: "sk",
    MSG_PING: "pi",
    MSG_PONG: "po",
}
_CODE_TO_TYPE = {v: k for k, v in _TYPE_TO_CODE.items()}

# Short field names for high-frequency messages
_FIELD_SHORT = {
    "player_id": "p", "x": "x", "y": "y",
    "health": "h", "max_health": "mh",
    "is_dead": "d", "enemy_id": "ei",
    "enemies": "e", "level": "l",
}
_FIELD_LONG = {v: k for k, v in _FIELD_SHORT.items()}


def encode_message(msg_type, data=None):
    """Encode a message as length-prefixed JSON bytes.
    Uses short codes for high-frequency message types to reduce bandwidth."""
    code = _TYPE_TO_CODE.get(msg_type, msg_type)
    payload = {"t": code, "d": data or {}}
    raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    return struct.pack('!I', len(raw)) + raw


def decode_messages(buffer):
    """
    Decode one or more messages from a byte buffer.
    Returns (list_of_messages, remaining_buffer).
    """
    messages = []
    while len(buffer) >= 4:
        msg_len = struct.unpack('!I', buffer[:4])[0]
        if msg_len > 1048576:  # 1MB sanity check
            buffer = buffer[4:]
            continue
        if len(buffer) < 4 + msg_len:
            break
        raw = buffer[4:4 + msg_len]
        buffer = buffer[4 + msg_len:]
        try:
            msg = json.loads(raw)
            # Translate short codes back to full names
            if "t" in msg:
                full_type = _CODE_TO_TYPE.get(msg["t"], msg["t"])
                messages.append({"type": full_type, "data": msg.get("d", {})})
            else:
                # Legacy format
                messages.append(msg)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return messages, buffer


def configure_socket(sock):
    """Apply optimal settings to a game socket."""
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's
    except Exception:
        pass
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
    except Exception:
        pass


def get_local_ip():
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"