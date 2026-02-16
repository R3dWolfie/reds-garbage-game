# game_state.py
"""
Central shared state for the game.
Every module imports from here instead of passing globals around.
"""

import pygame
import sys
import core.settings as settings_module
from core.settings import *
from entities.player_default import PlayerDefault
from entities.player_tank import PlayerTank
from entities.player_laser import PlayerLaser
from updater.version import GAME_NAME, VERSION
from core.sound_manager import SoundManager
from networking.net_common import *

# ---- Additional message types not in net_common ----
MSG_PARTY_LEVEL_UP = "party_level_up"
MSG_UPGRADE_PAUSE = "upgrade_pause"
MSG_UPGRADE_RESUME = "upgrade_resume"
MSG_WAVE_COMPLETE = "wave_complete"
MSG_ENEMY_DEAD = "enemy_dead"
MSG_ORB_SPAWN = "orb_spawn"
MSG_USERNAME = "username"

# ---- Initialize pygame ----
pygame.init()
pygame.mixer.init()

# ---- Class registry ----
PLAYER_CLASSES = {
    "default": PlayerDefault,
    "tank": PlayerTank,
    "laser": PlayerLaser,
}


# ===========================================================
#                   DISPLAY MANAGER
# ===========================================================

class DisplayManager:
    def __init__(self):
        self.config = settings_module.config
        self.screen = None
        self.apply()

    def apply(self):
        w, h = self.config["resolution"]

        if self.config["fullscreen"]:
            self.screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN | pygame.SCALED)
        else:
            self.screen = pygame.display.set_mode((w, h))

        pygame.display.set_caption("Red's Garbage Game")
        settings_module.SCREEN_WIDTH = w
        settings_module.SCREEN_HEIGHT = h

    def set_resolution(self, res):
        self.config["resolution"] = list(res)
        self.apply()

    def toggle_fullscreen(self):
        self.config["fullscreen"] = not self.config["fullscreen"]
        self.apply()

    def set_fullscreen(self, val):
        self.config["fullscreen"] = val
        self.apply()

    def get_screen(self):
        return self.screen

    def get_resolution(self):
        return (settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT)

    # ---- Volume controls (used by SettingsMenu) ----
    def set_master_volume(self, val):
        self.config["master_volume"] = val
        settings_module.save_config(self.config)

    def set_sfx_volume(self, val):
        self.config["sfx_volume"] = val
        settings_module.save_config(self.config)

    def set_music_volume(self, val):
        self.config["music_volume"] = val
        settings_module.save_config(self.config)


display_mgr = DisplayManager()
screen = display_mgr.get_screen()

# Clipboard support (requires display)
try:
    pygame.scrap.init()
except Exception:
    pass

# ---- Sound manager ----
sounds = SoundManager(settings_module.config)

# ---- Screen shake state ----
_shake_frames = 0
_shake_intensity = 0


def trigger_shake(frames=6, intensity=5):
    global _shake_frames, _shake_intensity
    _shake_frames = max(_shake_frames, frames)
    _shake_intensity = max(_shake_intensity, intensity)


def get_shake():
    """Return current shake state and decrement. Returns (frames, intensity)."""
    global _shake_frames, _shake_intensity
    return _shake_frames, _shake_intensity


def consume_shake():
    """Call once per frame after reading shake values."""
    global _shake_frames, _shake_intensity
    if _shake_frames > 0:
        _shake_frames -= 1
        if _shake_frames == 0:
            _shake_intensity = 0


# ---- Clock ----
clock = pygame.time.Clock()

# ---- Fonts ----
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 14)
title_font = pygame.font.SysFont("Arial", 40)
boss_font = pygame.font.SysFont("Arial", 30, bold=True)
menu_font = pygame.font.SysFont("Arial", 24)
header_font = pygame.font.SysFont("Arial", 50, bold=True)
desc_font = pygame.font.SysFont("Arial", 16, italic=True)


# ===========================================================
#             MUTABLE GLOBAL STATE (network, etc.)
# ===========================================================

class _GameState:
    """Namespace for mutable globals that multiple modules need to read/write."""
    net_host = None
    net_client = None
    net_mode = None          # "host", "client", or None
    remote_players = {}      # {player_id: RemotePlayerGhost}
    remote_enemies = {}      # {enemy_id: RemoteEnemyGhost}
    upgrade_paused_by = None # None or {"player_name": str, "level": int}
    local_username = settings_module.config.get("username", "Player")


gs = _GameState()