# player_default.py
from settings import *
from player_base import PlayerBase


class PlayerDefault(PlayerBase):
    """The Survivor - balanced all-rounder with auto-firing bullets."""

    CLASS_KEY = "default"
    DISPLAY_NAME = "Survivor"
    SPRITE_FILE = "player_default.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = GREEN

    BASE_STATS = {
        "speed": 4,
        "fire_rate": 60,
        "bullet_speed": 7,
        "max_health": 100,
        "multishot": 1,
        "damage": 1,
        "piercing": 1,
        "magnet": 0,
        "bullet_size": 1,
    }

    def get_weapon_type(self):
        return "bullet"