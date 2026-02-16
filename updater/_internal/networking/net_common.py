# networking/net_common.py
"""
Shared protocol definitions for P2P multiplayer.
Uses raw TCP sockets with JSON messages.
"""

import json
import struct
import socket

DEFAULT_PORT = 27015
BUFFER_SIZE = 4096

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
MSG_UPGRADE_PAUSE = "upgrade_pause"
MSG_UPGRADE_RESUME = "upgrade_resume"
MSG_PARTY_LEVEL_UP = "party_level_up"
MSG_UPGRADE_DONE = "upgrade_done"


def encode_message(msg_type, data=None):
    """Encode a message as length-prefixed JSON bytes."""
    payload = {"type": msg_type, "data": data or {}}
    raw = json.dumps(payload).encode('utf-8')
    length = struct.pack('!I', len(raw))
    return length + raw


def decode_messages(buffer):
    """
    Decode one or more messages from a byte buffer.
    Returns (list_of_messages, remaining_buffer).
    """
    messages = []
    while len(buffer) >= 4:
        msg_len = struct.unpack('!I', buffer[:4])[0]
        if len(buffer) < 4 + msg_len:
            break
        raw = buffer[4:4 + msg_len]
        buffer = buffer[4 + msg_len:]
        try:
            msg = json.loads(raw.decode('utf-8'))
            messages.append(msg)
        except json.JSONDecodeError:
            pass
    return messages, buffer


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