# player_base.py
import pygame
import math
from settings import *
from sprite_loader import load_sprite


class PlayerBase(pygame.sprite.Sprite):
    """Base class for all player classes."""

    CLASS_KEY = "base"
    DISPLAY_NAME = "Base"
    SPRITE_FILE = "player_default.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = GREEN  # Fallback color

    # Default base stats (subclasses override these)
    BASE_STATS = {
        "speed": 4,
        "fire_rate": 60,
        "bullet_speed": 7,
        "max_health": 100,
        "multishot": 1,
        "damage": 1,
        "piercing": 1,
        "magnet": 0,
    }

    def __init__(self):
        super().__init__()
        self.image = load_sprite(self.SPRITE_FILE, self.SPRITE_SIZE, self.SPRITE_COLOR, self.SPRITE_SIZE)
        self.original_image = self.image.copy()
        self.hurt_image = load_sprite(self.SPRITE_FILE, self.SPRITE_SIZE, RED, self.SPRITE_SIZE)
        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        # Copy base stats
        self.stats = dict(self.BASE_STATS)
        self.current_health = self.stats["max_health"]
        self.last_hit = 0

        # Upgrade counters
        self.upgrade_counts = {
            "speed": 0,
            "fire_rate": 0,
            "bullet_speed": 0,
            "max_health": 0,
            "multishot": 0,
            "damage": 0,
            "piercing": 0,
            "magnet": 0,
        }

        # Leveling
        self.level = 1
        self.current_xp = 0
        self.xp_to_next_level = 5

        # Collision damage (for tank class)
        self.collision_damage = 0
        self.collision_cooldown = 0

    def reposition(self, sw, sh):
        self.rect.center = (sw // 2, sh // 2)

    def update(self):
        keys = pygame.key.get_pressed()
        speed = self.stats["speed"]

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.rect.y -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.rect.y += speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.rect.x -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.rect.x += speed

        sw = SCREEN_WIDTH
        sh = SCREEN_HEIGHT
        self.rect.clamp_ip(pygame.Rect(0, 0, sw, sh))

        # Reduce collision cooldown
        if self.collision_cooldown > 0:
            self.collision_cooldown -= 1

    def heal(self, amount):
        self.current_health = min(self.current_health + amount, self.stats["max_health"])

    def get_magnet_radius(self):
        return BASE_MAGNET_RADIUS + (self.stats["magnet"] * MAGNET_PER_UPGRADE)

    def set_hurt(self, is_hurt):
        """Toggle between normal and hurt sprite."""
        if is_hurt:
            self.image = self.hurt_image.copy()
        else:
            self.image = self.original_image.copy()

    def apply_upgrade(self, upgrade_key):
        # ---- Normal ----
        if upgrade_key == "speed":
            self.stats["speed"] += 1
            self.upgrade_counts["speed"] += 1
        elif upgrade_key == "fire_rate":
            self.stats["fire_rate"] = max(5, int(self.stats["fire_rate"] * 0.9))
            self.upgrade_counts["fire_rate"] += 1
        elif upgrade_key == "bullet_speed":
            self.stats["bullet_speed"] += 2
            self.upgrade_counts["bullet_speed"] += 1
        elif upgrade_key == "max_health":
            self.stats["max_health"] += 20
            self.current_health += 20
            self.upgrade_counts["max_health"] += 1
        elif upgrade_key == "multishot":
            self.stats["multishot"] += 1
            self.upgrade_counts["multishot"] += 1
        elif upgrade_key == "damage":
            self.stats["damage"] += 1
            self.upgrade_counts["damage"] += 1
        elif upgrade_key == "piercing":
            self.stats["piercing"] += 1
            self.upgrade_counts["piercing"] += 1
        elif upgrade_key == "magnet":
            self.stats["magnet"] += 1
            self.upgrade_counts["magnet"] += 1

        # ---- Big ----
        elif upgrade_key == "big_speed":
            self.stats["speed"] += 3
            self.upgrade_counts["speed"] += 3
        elif upgrade_key == "big_fire_rate":
            self.stats["fire_rate"] = max(5, int(self.stats["fire_rate"] * 0.7))
            self.upgrade_counts["fire_rate"] += 3
        elif upgrade_key == "big_bullet_speed":
            self.stats["bullet_speed"] += 5
            self.upgrade_counts["bullet_speed"] += 3
        elif upgrade_key == "big_max_health":
            self.stats["max_health"] += 50
            self.current_health = self.stats["max_health"]
            self.upgrade_counts["max_health"] += 3
        elif upgrade_key == "big_multishot":
            self.stats["multishot"] += 2
            self.upgrade_counts["multishot"] += 2
        elif upgrade_key == "big_damage":
            self.stats["damage"] += 3
            self.upgrade_counts["damage"] += 3
        elif upgrade_key == "big_piercing":
            self.stats["piercing"] += 3
            self.upgrade_counts["piercing"] += 3
        elif upgrade_key == "big_magnet":
            self.stats["magnet"] += 3
            self.upgrade_counts["magnet"] += 3

    def get_weapon_type(self):
        """Override in subclass. Returns 'bullet', 'laser', 'ram', etc."""
        return "bullet"

    def draw_magnet_ring(self, surf):
        """Draw the magnet radius as a faint circle."""
        radius = self.get_magnet_radius()
        if radius > 0:
            ring_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (0, 255, 255, 30), (radius, radius), radius)
            pygame.draw.circle(ring_surf, (0, 255, 255, 60), (radius, radius), radius, 1)
            surf.blit(ring_surf, (self.rect.centerx - radius, self.rect.centery - radius))
