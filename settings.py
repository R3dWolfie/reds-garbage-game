# settings.py
import json
import os

# ---- Default Config ----
DEFAULT_CONFIG = {
    "resolution": [1920, 1080],
    "fullscreen": True,
    "master_volume": 0.7,
    "sfx_volume": 0.7,
    "music_volume": 0.5,
}

# Old defaults we want to upgrade away from automatically
_OLD_DEFAULTS = {
    "resolution": [1280, 720],
    "fullscreen": False,
}

CONFIG_FILE = "config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            # Fill in any missing keys
            for key in DEFAULT_CONFIG:
                if key not in data:
                    data[key] = DEFAULT_CONFIG[key]
            # Migrate old default values to new defaults
            # (only if the player hasn't customised them away from the old default)
            for key, old_val in _OLD_DEFAULTS.items():
                if data.get(key) == old_val:
                    data[key] = DEFAULT_CONFIG[key]
            return data
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


config = load_config()

SCREEN_WIDTH = config["resolution"][0]
SCREEN_HEIGHT = config["resolution"][1]
FPS = 60

RESOLUTIONS = [
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
]

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
LIGHT_GRAY = (170, 170, 170)
PINK = (255, 100, 200)
ORANGE = (255, 165, 0)
PURPLE = (150, 0, 255)
GOLD = (255, 215, 0)
DARK_RED = (150, 0, 0)
STEEL_BLUE = (70, 130, 180)
LASER_RED = (255, 50, 50)

# Game Constants
HEALTH_ORB_DROP_CHANCE = 0.15
HEALTH_ORB_HEAL = 10
BASE_MAGNET_RADIUS = 0  # No magnet by default
MAGNET_PER_UPGRADE = 50  # Pixels added per magnet upgrade

# Normal Upgrade Pool
UPGRADE_POOL = [
    {"key": "speed",        "name": "Move Speed +1",       "desc": "Move faster"},
    {"key": "fire_rate",    "name": "Fire Rate +10%",      "desc": "Shoot more often"},
    {"key": "bullet_speed", "name": "Bullet Speed +2",     "desc": "Bullets fly faster"},
    {"key": "max_health",   "name": "Max Health +20",      "desc": "More survivability"},
    {"key": "multishot",    "name": "Multishot +1",        "desc": "Hit more targets"},
    {"key": "damage",       "name": "Damage +1",           "desc": "Hit harder"},
    {"key": "piercing",     "name": "Piercing +1",         "desc": "Bullets pass through"},
    {"key": "magnet",       "name": "Magnet +50px",        "desc": "Pull XP from further"},
]

# Big Upgrade Pool (every 5 levels)
BIG_UPGRADE_POOL = [
    {"key": "big_speed",        "name": "★ Move Speed +3",            "desc": "Major speed boost"},
    {"key": "big_fire_rate",    "name": "★ Fire Rate +30%",           "desc": "Much faster shooting"},
    {"key": "big_bullet_speed", "name": "★ Bullet Speed +5",          "desc": "Blazing bullets"},
    {"key": "big_max_health",   "name": "★ Max HP +50 & Full Heal",   "desc": "Tank up completely"},
    {"key": "big_multishot",    "name": "★ Multishot +2",             "desc": "Spray and pray"},
    {"key": "big_damage",       "name": "★ Damage +3",                "desc": "Massive damage boost"},
    {"key": "big_piercing",     "name": "★ Piercing +3",              "desc": "Bullets shred through"},
    {"key": "big_magnet",       "name": "★ Magnet +150px",            "desc": "Vacuum everything"},
]

# Class Definitions (for selection screen)
CLASS_INFO = {
    "default": {
        "name": "Survivor",
        "color": GREEN,
        "desc": "Balanced fighter. Auto-fires bullets at nearby enemies.",
        "icon_color": GREEN,
    },
    "tank": {
        "name": "Juggernaut",
        "color": STEEL_BLUE,
        "desc": "High HP, rams enemies for collision damage. Slower but tough.",
        "icon_color": STEEL_BLUE,
    },
    "laser": {
        "name": "Arcanist",
        "color": LASER_RED,
        "desc": "Fires slow but devastating laser beams that pierce all.",
        "icon_color": LASER_RED,
    },
}