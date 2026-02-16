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
    "username": "Player",
    "mouse_move": False,
    "gold": 0,
    "highest_wave": 1,
    "perma_upgrades": {
        "roomba_count": 0,
        "roomba_speed": 0,
        "saw_count": 0,
        "saw_damage": 0,
        "saw_speed": 0,
        "crit_chance": 0,
        "base_magnet": 0,
        "gold_magnet": 0,
        "armor": 0,
        "xp_bonus": 0,
        "starting_hp": 0,
        "gold_rush": 0,
        "revival": 0,
        "roomba_range": 0,
        "dash_power": 0,
        "health_regen": 0,
        "dodge_chance": 0,
        "thorns": 0,
        "move_speed": 0,
        "fire_rate_boost": 0,
        "bullet_ricochet": 0,
        "roomba_damage": 0,
        "saw_size": 0,
        "shield": 0,
        "lucky_drops": 0,
    },
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
            # Fill in any missing perma_upgrades sub-keys
            default_perma = DEFAULT_CONFIG.get("perma_upgrades", {})
            current_perma = data.get("perma_upgrades", {})
            for pkey in default_perma:
                if pkey not in current_perma:
                    current_perma[pkey] = default_perma[pkey]
            data["perma_upgrades"] = current_perma
            # Migrate old default values to new defaults
            # (only if the player hasn't customised them away from the old default)
            for key, old_val in _OLD_DEFAULTS.items():
                if data.get(key) == old_val:
                    data[key] = DEFAULT_CONFIG[key]
            return data
        except Exception:
            return DEFAULT_CONFIG.copy()
    # First launch — write defaults so the file exists going forward
    defaults = DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(defaults, f, indent=2)
    except Exception:
        pass
    return defaults


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

# Neon Colors
NEON_CYAN = (0, 255, 255)
NEON_PINK = (255, 0, 200)
NEON_GREEN = (57, 255, 20)
NEON_BLUE = (0, 150, 255)
NEON_PURPLE = (180, 0, 255)
NEON_ORANGE = (255, 100, 0)
NEON_YELLOW = (255, 255, 0)
NEON_RED = (255, 30, 60)

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
    {"key": "bullet_size",  "name": "Bullet Size +30%",    "desc": "Bigger hitbox, +0.5 damage"},
    {"key": "xp_gain",      "name": "XP Gain +25%",        "desc": "Level up faster"},
    {"key": "accuracy",     "name": "Accuracy Up",          "desc": "Tighter bullet cone spread"},
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
    {"key": "big_bullet_size",  "name": "★ Bullet Size +80%",         "desc": "Massive projectiles, +1 damage"},
    {"key": "big_xp_gain",      "name": "★ XP Gain +75%",             "desc": "Turbo leveling"},
    {"key": "big_accuracy",     "name": "★ Laser Accuracy",           "desc": "Extremely tight cone spread"},
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

# ---- Gold / Perma Shop ----
GOLD_DROP_CHANCE = 0.25  # 25% chance per enemy kill
GOLD_DROP_CHANCE_BOSS = 1.0  # Bosses always drop gold
GOLD_VALUE_MIN = 1
GOLD_VALUE_MAX = 3
GOLD_BOSS_VALUE = 10

# Perma Shop Items: key, name, desc, max_level, costs (list per level), stat info
PERMA_SHOP_ITEMS = [
    {
        "key": "roomba_count",
        "name": "XP Roomba",
        "desc": "Orbital roomba that auto-collects XP gems",
        "icon_color": CYAN,
        "max_level": 15,
        "costs": [10, 25, 50, 100, 200, 350, 550, 800, 1100, 1500, 2000, 2800, 3800, 5000, 7000],
        "stat_per_level": "+1 roomba",
    },
    {
        "key": "roomba_speed",
        "name": "Roomba Speed",
        "desc": "Roombas orbit faster and cover more ground",
        "icon_color": (0, 200, 200),
        "max_level": 10,
        "costs": [8, 18, 35, 70, 140, 240, 380, 560, 800, 1100],
        "stat_per_level": "+25% orbit speed",
    },
    {
        "key": "saw_count",
        "name": "Spinning Saw",
        "desc": "Orbital saw blade that damages enemies on contact",
        "icon_color": (200, 200, 200),
        "max_level": 10,
        "costs": [15, 35, 70, 140, 280, 480, 750, 1100, 1600, 2200],
        "stat_per_level": "+1 saw",
    },
    {
        "key": "saw_damage",
        "name": "Saw Sharpness",
        "desc": "Each saw deals more damage per hit",
        "icon_color": (220, 180, 180),
        "max_level": 10,
        "costs": [10, 22, 45, 90, 180, 300, 460, 660, 920, 1250],
        "stat_per_level": "+2 damage",
    },
    {
        "key": "saw_speed",
        "name": "Saw Speed",
        "desc": "Saws orbit faster around you",
        "icon_color": (180, 180, 220),
        "max_level": 5,
        "costs": [8, 18, 35, 70, 140],
        "stat_per_level": "+20% orbit speed",
    },
    {
        "key": "crit_chance",
        "name": "Critical Strike",
        "desc": "Chance for bullets to deal 2x damage",
        "icon_color": (255, 80, 80),
        "max_level": 10,
        "costs": [10, 15, 25, 40, 60, 85, 115, 150, 200, 260],
        "stat_per_level": "+5% crit chance",
    },
    {
        "key": "base_magnet",
        "name": "Magnet Aura",
        "desc": "Start each run with extra XP magnet range",
        "icon_color": (100, 200, 255),
        "max_level": 8,
        "costs": [5, 12, 22, 38, 60, 90, 130, 180],
        "stat_per_level": "+30px magnet range",
    },
    {
        "key": "gold_magnet",
        "name": "Gold Magnet",
        "desc": "Gold coins are pulled toward you from further away",
        "icon_color": GOLD,
        "max_level": 5,
        "costs": [8, 18, 35, 65, 120],
        "stat_per_level": "+40px gold pickup range",
    },
    {
        "key": "armor",
        "name": "Armor Plating",
        "desc": "Reduce all damage taken",
        "icon_color": STEEL_BLUE,
        "max_level": 10,
        "costs": [12, 28, 55, 110, 220, 380, 580, 830, 1150, 1550],
        "stat_per_level": "-5% damage taken",
    },
    {
        "key": "xp_bonus",
        "name": "XP Bonus",
        "desc": "Chance to get double XP from gems",
        "icon_color": (150, 100, 255),
        "max_level": 5,
        "costs": [10, 22, 45, 90, 180],
        "stat_per_level": "+10% double XP chance",
    },
    {
        "key": "starting_hp",
        "name": "Vitality",
        "desc": "Start each run with bonus max HP",
        "icon_color": (255, 100, 150),
        "max_level": 10,
        "costs": [8, 18, 35, 65, 120, 200, 320, 480, 700, 1000],
        "stat_per_level": "+15 max HP",
    },
    {
        "key": "gold_rush",
        "name": "Gold Rush",
        "desc": "Enemies drop gold more often",
        "icon_color": (255, 200, 50),
        "max_level": 10,
        "costs": [15, 35, 70, 140, 280, 460, 700, 1000, 1400, 1900],
        "stat_per_level": "+8% gold drop chance",
    },
    {
        "key": "revival",
        "name": "Second Wind",
        "desc": "Revive once per run with 50% HP",
        "icon_color": (100, 255, 100),
        "max_level": 5,
        "costs": [50, 150, 400, 800, 1500],
        "stat_per_level": "+1 revival per run",
    },
    {
        "key": "roomba_range",
        "name": "Roomba Range",
        "desc": "Roombas scan further and roam further from you",
        "icon_color": (0, 220, 180),
        "max_level": 10,
        "costs": [10, 22, 45, 90, 180, 320, 500, 750, 1100, 1600],
        "stat_per_level": "+40% scan & leash range",
    },
    {
        "key": "roomba_damage",
        "name": "Roomba Zap",
        "desc": "Roombas zap nearby enemies for damage on contact",
        "icon_color": (0, 255, 200),
        "max_level": 10,
        "costs": [15, 35, 65, 110, 180, 280, 420, 600, 850, 1200],
        "stat_per_level": "+3 zap damage",
    },
    {
        "key": "dash_power",
        "name": "Dash Power",
        "desc": "Shorter dash cooldown and longer dash distance",
        "icon_color": (100, 200, 255),
        "max_level": 20,
        "costs": [8, 15, 25, 40, 60, 85, 115, 150, 200, 260, 340, 440, 560, 700, 880, 1100, 1400, 1800, 2300, 3000],
        "stat_per_level": "-4f cooldown, +1f duration",
    },
    {
        "key": "health_regen",
        "name": "Regeneration",
        "desc": "Slowly regenerate HP over time during combat",
        "icon_color": (50, 255, 120),
        "max_level": 10,
        "costs": [12, 28, 55, 100, 170, 270, 400, 580, 800, 1100],
        "stat_per_level": "+0.5 HP/sec",
    },
    {
        "key": "dodge_chance",
        "name": "Phase Dodge",
        "desc": "Chance to phase through incoming damage",
        "icon_color": (200, 150, 255),
        "max_level": 10,
        "costs": [15, 35, 65, 110, 180, 280, 420, 600, 850, 1200],
        "stat_per_level": "+4% dodge chance",
    },
    {
        "key": "thorns",
        "name": "Thorn Aura",
        "desc": "Enemies that hit you take damage back",
        "icon_color": (255, 80, 150),
        "max_level": 8,
        "costs": [10, 25, 50, 100, 200, 350, 550, 800],
        "stat_per_level": "+5 thorns damage",
    },
    {
        "key": "move_speed",
        "name": "Swift Boots",
        "desc": "Start each run with bonus movement speed",
        "icon_color": (100, 255, 200),
        "max_level": 8,
        "costs": [8, 18, 35, 65, 110, 180, 280, 420],
        "stat_per_level": "+1 move speed",
    },
    {
        "key": "fire_rate_boost",
        "name": "Trigger Finger",
        "desc": "Start each run shooting faster",
        "icon_color": (255, 150, 50),
        "max_level": 8,
        "costs": [10, 22, 45, 90, 170, 280, 430, 650],
        "stat_per_level": "-8% fire delay",
    },
    {
        "key": "bullet_ricochet",
        "name": "Ricochet",
        "desc": "Bullets bounce off screen edges back into the fray",
        "icon_color": (255, 255, 100),
        "max_level": 3,
        "costs": [30, 100, 300],
        "stat_per_level": "+1 bounce",
    },
    {
        "key": "saw_size",
        "name": "Saw Growth",
        "desc": "Orbital saws are larger with bigger hitbox",
        "icon_color": (180, 200, 220),
        "max_level": 5,
        "costs": [12, 28, 55, 110, 220],
        "stat_per_level": "+20% saw size",
    },
    {
        "key": "shield",
        "name": "Energy Shield",
        "desc": "Absorb one hit every few seconds",
        "icon_color": (80, 200, 255),
        "max_level": 5,
        "costs": [25, 65, 150, 350, 700],
        "stat_per_level": "-3s shield recharge",
    },
    {
        "key": "lucky_drops",
        "name": "Lucky Drops",
        "desc": "Enemies drop more and better loot",
        "icon_color": (255, 200, 100),
        "max_level": 8,
        "costs": [10, 22, 45, 90, 170, 280, 430, 650],
        "stat_per_level": "+8% extra drop chance",
    },
]