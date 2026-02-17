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

# ---- Set SDL hints BEFORE pygame.init() ----
import os
import platform
# Note: Do NOT set SDL_VIDEO_HIGHDPI_DISABLED on macOS
# pygame works in "points" on Retina and SCALED handles the rest

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
    """Manages display. Always renders at 1920x1080 internal resolution.
    pygame.SCALED handles stretching to the actual window/monitor size."""
    def __init__(self):
        self.config = settings_module.config
        self.screen = None
        self._actual_w = 1920
        self._actual_h = 1080
        self._windowed = False
        self._render_surface = None
        self.apply()

    def apply(self):
        # The config "resolution" is the desired *display* size,
        # but we always render internally at 1920x1080.
        display_w, display_h = self.config["resolution"]
        fullscreen = self.config.get("fullscreen", True)
        borderless = self.config.get("borderless", False)
        fps = self.config.get("fps", 60)

        # Always render at fixed internal resolution
        internal_w = settings_module.INTERNAL_WIDTH
        internal_h = settings_module.INTERNAL_HEIGHT

        import platform
        is_macos = platform.system() == "Darwin"

        if fullscreen:
            if is_macos:
                # macOS: use borderless window sized to avoid the notch
                # Get usable screen area (excludes menu bar and notch)
                try:
                    desktop_sizes = pygame.display.get_desktop_sizes()
                    desk_w, desk_h = desktop_sizes[0] if desktop_sizes else (1920, 1080)
                except Exception:
                    desk_w, desk_h = 1920, 1080

                # Use 16:10 aspect ratio to avoid notch area
                # Calculate the largest 16:10 area that fits
                target_w = desk_w
                target_h = int(desk_w * 10 / 16)
                if target_h > desk_h:
                    target_h = desk_h
                    target_w = int(desk_h * 16 / 10)

                flags = pygame.NOFRAME
                try:
                    # Position window at bottom of screen to avoid notch
                    os.environ['SDL_VIDEO_WINDOW_POS'] = f'0,{desk_h - target_h}'
                    self.screen = pygame.display.set_mode((target_w, target_h), flags)
                except Exception:
                    self.screen = pygame.display.set_mode((desk_w, desk_h), flags)

                actual_w, actual_h = self.screen.get_size()
                if (actual_w, actual_h) != (internal_w, internal_h):
                    self._render_surface = pygame.Surface((internal_w, internal_h))
                else:
                    self._render_surface = None
            else:
                # Windows/Linux: fullscreen at selected resolution
                try:
                    self.screen = pygame.display.set_mode((display_w, display_h), pygame.FULLSCREEN)
                except Exception:
                    try:
                        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    except Exception:
                        self.screen = pygame.display.set_mode((internal_w, internal_h))

                actual_w, actual_h = self.screen.get_size()
                if (actual_w, actual_h) != (internal_w, internal_h):
                    self._render_surface = pygame.Surface((internal_w, internal_h))
                else:
                    self._render_surface = None
        else:
            # Windowed at selected resolution
            flags = pygame.NOFRAME if borderless else 0
            try:
                self.screen = pygame.display.set_mode((display_w, display_h), flags)
            except Exception:
                self.screen = pygame.display.set_mode((1920, 1080))
            self._render_surface = pygame.Surface((internal_w, internal_h))

        self._windowed = self._render_surface is not None

        pygame.display.set_caption("Red's Garbage Game")

        # Internal resolution is always fixed
        settings_module.SCREEN_WIDTH = internal_w
        settings_module.SCREEN_HEIGHT = internal_h
        settings_module.FPS = fps
        self._actual_w = display_w
        self._actual_h = display_h

        # Rebuild fonts (fixed sizes, no scaling needed)
        try:
            _build_fonts()
        except Exception:
            pass

        # Reset clock to prevent huge dt spike after display mode change
        try:
            clock.tick(fps if fps > 0 else 60)
        except Exception:
            pass

    def get_screen(self):
        """Return the surface to draw on. Always 1920x1080."""
        if self._render_surface is not None:
            return self._render_surface
        return self.screen

    def present(self):
        """Present the frame. Scale internal surface to actual screen."""
        if self._render_surface is not None:
            win_w, win_h = self.screen.get_size()
            scaled = pygame.transform.smoothscale(self._render_surface, (win_w, win_h))
            self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def get_mouse_pos(self):
        """Get mouse position mapped to internal 1920x1080 coordinates."""
        mx, my = _original_get_pos()
        if self._render_surface is not None:
            win_w, win_h = self.screen.get_size()
            int_w, int_h = self._render_surface.get_size()
            if win_w > 0 and win_h > 0:
                mx = int(mx * int_w / win_w)
                my = int(my * int_h / win_h)
        return mx, my

    def _scale_pos(self, pos):
        """Scale a screen position to internal coordinates."""
        if self._render_surface is not None:
            win_w, win_h = self.screen.get_size()
            int_w, int_h = self._render_surface.get_size()
            if win_w > 0 and win_h > 0:
                return (int(pos[0] * int_w / win_w), int(pos[1] * int_h / win_h))
        return pos

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

# Monkey-patch pygame.mouse.get_pos so all existing code
# automatically gets coordinates in internal 1920x1080 space
_original_get_pos = pygame.mouse.get_pos
def _scaled_get_pos():
    return display_mgr.get_mouse_pos()
pygame.mouse.get_pos = _scaled_get_pos

# Monkey-patch pygame.event.get to translate mouse event positions
_original_event_get = pygame.event.get
_MOUSE_EVENTS = {pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION}
def _scaled_event_get(*args, **kwargs):
    events = _original_event_get(*args, **kwargs)
    for ev in events:
        if ev.type in _MOUSE_EVENTS and hasattr(ev, 'pos'):
            # Create new event with translated pos
            ev.__dict__['pos'] = display_mgr._scale_pos(ev.pos)
    return events
pygame.event.get = _scaled_event_get

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

# ---- Fonts (fixed sizes — internal resolution is always 1920x1080) ----
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 14)
title_font = pygame.font.SysFont("Arial", 40)
boss_font = pygame.font.SysFont("Arial", 30, bold=True)
menu_font = pygame.font.SysFont("Arial", 24)
header_font = pygame.font.SysFont("Arial", 50, bold=True)
desc_font = pygame.font.SysFont("Arial", 16, italic=True)

def _build_fonts():
    """Rebuild all fonts. Fixed sizes since internal resolution is always 1080p."""
    import core.game_state as _self
    _self.font = pygame.font.SysFont("Arial", 18)
    _self.small_font = pygame.font.SysFont("Arial", 14)
    _self.title_font = pygame.font.SysFont("Arial", 40)
    _self.boss_font = pygame.font.SysFont("Arial", 30, bold=True)
    _self.menu_font = pygame.font.SysFont("Arial", 24)
    _self.header_font = pygame.font.SysFont("Arial", 50, bold=True)
    _self.desc_font = pygame.font.SysFont("Arial", 16, italic=True)


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