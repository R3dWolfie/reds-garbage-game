# player_laser.py
import pygame
import math
from settings import *
from player_base import PlayerBase


class PlayerLaser(PlayerBase):
    """The Arcanist - fires slow but devastating laser beams that pierce all enemies."""

    CLASS_KEY = "laser"
    DISPLAY_NAME = "Arcanist"
    SPRITE_FILE = "player_laser.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = LASER_RED

    BASE_STATS = {
        "speed": 4,
        "fire_rate": 120,       # Very slow fire rate
        "bullet_speed": 4,      # Slow beams
        "max_health": 80,       # Fragile
        "multishot": 1,
        "damage": 5,            # High damage
        "piercing": 999,        # Infinite pierce
        "magnet": 0,
        "bullet_size": 1,
    }

    def get_weapon_type(self):
        return "laser"