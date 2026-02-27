# player_default.py
from core.settings import *
from entities.player_base import PlayerBase


class PlayerDefault(PlayerBase):
    """The Survivor - balanced all-rounder with auto-firing bullets."""

    CLASS_KEY = "default"
    DISPLAY_NAME = "Survivor"
    SPRITE_FILE = "player_default.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = GREEN
    NEON_GLOW_COLOR = (57, 255, 20)

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
        "xp_gain": 1.0,
        "accuracy": 1.0,
    }

    def get_weapon_type(self):
        return "bullet"

    def get_bullet_color(self):
        return (57, 255, 20)  # Green