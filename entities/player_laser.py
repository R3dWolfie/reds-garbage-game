# player_laser.py
import pygame
import math
from core.settings import *
from entities.player_base import PlayerBase


class PlayerLaser(PlayerBase):
    """The Arcanist - fires a devastating beam from player to screen edge."""

    CLASS_KEY = "laser"
    DISPLAY_NAME = "Arcanist"
    SPRITE_FILE = "player_laser.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = LASER_RED
    NEON_GLOW_COLOR = (255, 50, 80)

    BASE_STATS = {
        "speed": 4,
        "fire_rate": 80,        # Slow fire rate
        "bullet_speed": 4,      # Not used for beam but kept for compat
        "max_health": 80,       # Fragile
        "multishot": 1,         # Beam width multiplier via multishot
        "damage": 3,            # Damage per tick (beam hits multiple times)
        "piercing": 1,          # Beam always pierces, stat used for bounces
        "magnet": 0,
        "bullet_size": 1,       # Beam width multiplier
        "xp_gain": 1.0,
        "accuracy": 1.0,
        "bullet_bounces": 0,    # Gained via upgrades
    }

    def get_weapon_type(self):
        return "beam"