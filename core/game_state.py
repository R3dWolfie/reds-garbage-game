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
from entities.player_gunner import PlayerGunner
from entities.player_sniper import PlayerSniper
from entities.player_paladin import PlayerPaladin
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
    "gunner": PlayerGunner,
    "sniper": PlayerSniper,
    "paladin": PlayerPaladin,
}


# ===========================================================
#                   DISPLAY MANAGER
# ===========================================================

class DisplayManager:
    """Manages display. Uses pygame.SCALED for automatic resolution handling."""
    def __init__(self):
        self.config = settings_module.config
        self.screen = None
        self._actual_w = 1920
        self._actual_h = 1080
        self.apply()

    def apply(self):
        w, h = self.config["resolution"]
        fullscreen = self.config.get("fullscreen", True)
        borderless = self.config.get("borderless", False)
        fps = self.config.get("fps", 60)

        # pygame.SCALED handles all resolution scaling automatically
        # It renders at the requested resolution and scales to fit the window
        flags = pygame.SCALED
        if fullscreen:
            flags |= pygame.FULLSCREEN
        if borderless and not fullscreen:
            flags |= pygame.NOFRAME

        try:
            self.screen = pygame.display.set_mode((w, h), flags)
        except Exception:
            try:
                self.screen = pygame.display.set_mode((w, h))
            except Exception:
                self.screen = pygame.display.set_mode((1920, 1080))

        pygame.display.set_caption("Red's Garbage Game")
        settings_module.SCREEN_WIDTH = w
        settings_module.SCREEN_HEIGHT = h
        settings_module.FPS = fps
        self._actual_w = w
        self._actual_h = h

        # Rebuild fonts for new resolution
        try:
            _build_fonts()
        except Exception:
            pass

    def get_screen(self):
        return self.screen

    def present(self):
        pygame.display.flip()

    def set_resolution(self, res):
        self.config["resolution"] = list(res)
        self.apply()

    def toggle_fullscreen(self):
        self.config["fullscreen"] = not self.config["fullscreen"]
        self.apply()

    def set_fullscreen(self, val):
        self.config["fullscreen"] = val
        self.apply()

    def set_borderless(self, val):
        self.config["borderless"] = val
        self.apply()

    def set_vsync(self, val):
        self.config["vsync"] = val
        self.apply()

    def set_fps(self, fps):
        self.config["fps"] = fps
        settings_module.FPS = fps

    def get_resolution(self):
        return (settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT)

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

# ---- Fonts (scaled to resolution) ----
def _scaled_font_size(base_size, ref_height=1080):
    """Scale font size proportionally to screen height. Reference: 1080p."""
    h = settings_module.SCREEN_HEIGHT or 1080
    return max(8, int(base_size * h / ref_height))

# Initial fonts at default sizes — will be rebuilt when resolution is set
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 14)
title_font = pygame.font.SysFont("Arial", 40)
boss_font = pygame.font.SysFont("Arial", 30, bold=True)
menu_font = pygame.font.SysFont("Arial", 24)
header_font = pygame.font.SysFont("Arial", 50, bold=True)
desc_font = pygame.font.SysFont("Arial", 16, italic=True)

def _build_fonts():
    """Rebuild all fonts at the current resolution scale.
    Updates module-level globals so all importers see new fonts."""
    import core.game_state as _self
    _self.font = pygame.font.SysFont("Arial", _scaled_font_size(18))
    _self.small_font = pygame.font.SysFont("Arial", _scaled_font_size(14))
    _self.title_font = pygame.font.SysFont("Arial", _scaled_font_size(40))
    _self.boss_font = pygame.font.SysFont("Arial", _scaled_font_size(30), bold=True)
    _self.menu_font = pygame.font.SysFont("Arial", _scaled_font_size(24))
    _self.header_font = pygame.font.SysFont("Arial", _scaled_font_size(50), bold=True)
    _self.desc_font = pygame.font.SysFont("Arial", _scaled_font_size(16), italic=True)


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
    remote_helpers = {}      # {player_id: [{"type","x","y",...}, ...]}
    upgrade_paused_by = None # None or {"player_name": str, "level": int}
    local_username = settings_module.config.get("username", "Player")


gs = _GameState()