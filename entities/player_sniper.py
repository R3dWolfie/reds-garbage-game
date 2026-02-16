# player_sniper.py
import pygame
import math
from core.settings import *
from entities.player_base import PlayerBase


class PlayerSniper(PlayerBase):
    """The Sniper - slow fire, massive damage, high pierce and bullet speed."""

    CLASS_KEY = "sniper"
    DISPLAY_NAME = "Sniper"
    SPRITE_FILE = "player_default.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = (200, 50, 255)  # Purple
    NEON_GLOW_COLOR = (220, 100, 255)

    BASE_STATS = {
        "speed": 3,             # Slow
        "fire_rate": 90,        # Very slow fire
        "bullet_speed": 14,     # Blazing fast bullets
        "max_health": 70,       # Very fragile
        "multishot": 1,
        "damage": 8,            # Massive damage
        "piercing": 5,          # High pierce
        "magnet": 0,
        "bullet_size": 1.3,     # Bigger bullets
        "xp_gain": 1.0,
        "accuracy": 3.0,        # Extremely accurate (tighter cone)
    }

    def get_weapon_type(self):
        return "bullet"