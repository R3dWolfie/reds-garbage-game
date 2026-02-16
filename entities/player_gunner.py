# player_gunner.py
import pygame
import math
from core.settings import *
from entities.player_base import PlayerBase


class PlayerGunner(PlayerBase):
    """The Gunner - insane fire rate, wide spray, low per-bullet damage."""

    CLASS_KEY = "gunner"
    DISPLAY_NAME = "Gunner"
    SPRITE_FILE = "player_default.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = (255, 165, 0)  # Orange
    NEON_GLOW_COLOR = (255, 180, 50)

    BASE_STATS = {
        "speed": 4,
        "fire_rate": 12,        # Extremely fast fire
        "bullet_speed": 9,
        "max_health": 80,       # Fragile
        "multishot": 3,         # Starts with 3 bullets
        "damage": 0.5,            # Very low per-bullet
        "piercing": 1,
        "magnet": 0,
        "bullet_size": 0.7,     # Smaller bullets
        "xp_gain": 1.0,
        "accuracy": 0.5,        # Wide spread
    }

    def get_weapon_type(self):
        return "bullet"