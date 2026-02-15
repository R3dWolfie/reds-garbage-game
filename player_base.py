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
        "bullet_size": 1,
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
            "bullet_size": 0,
        }

        # Leveling
        self.level = 1
        self.current_xp = 0
        self.xp_to_next_level = 5

        # Collision damage (for tank class)
        self.collision_damage = 0
        self.collision_cooldown = 0

        # Dash state
        self.dash_cooldown = 0
        self.dash_cooldown_max = 90   # 1.5s at 60fps
        self.dash_duration = 0
        self.dash_duration_max = 10   # frames the dash lasts
        self.dash_dx = 0
        self.dash_dy = 0
        self.dash_invincible = False  # invincibility frames during dash

    def reposition(self, sw, sh):
        self.rect.center = (sw // 2, sh // 2)

    def update(self):
        keys = pygame.key.get_pressed()
        speed = self.stats["speed"]

        # Track movement direction for dash
        move_dx, move_dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    move_dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  move_dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  move_dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move_dx += 1

        # ---- DASH ----
        if self.dash_duration > 0:
            # Currently dashing — apply burst movement, ignore normal input
            self.rect.x += self.dash_dx
            self.rect.y += self.dash_dy
            self.dash_duration -= 1
            self.dash_invincible = True
            if self.dash_duration == 0:
                self.dash_invincible = False
        else:
            self.dash_invincible = False
            self.rect.x += move_dx * speed
            self.rect.y += move_dy * speed

        # Cooldown tick
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        sw = SCREEN_WIDTH
        sh = SCREEN_HEIGHT
        self.rect.clamp_ip(pygame.Rect(0, 0, sw, sh))

        # Reduce collision cooldown
        if self.collision_cooldown > 0:
            self.collision_cooldown -= 1

    def try_dash(self):
        """Called when Space is pressed. Returns True if dash triggered."""
        if self.dash_cooldown > 0 or self.dash_duration > 0:
            return False
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        # Default dash: forward (up) if no direction held
        if dx == 0 and dy == 0:
            dy = -1
        dist = math.hypot(dx, dy)
        dash_speed = self.stats["speed"] * 5
        self.dash_dx = int((dx / dist) * dash_speed)
        self.dash_dy = int((dy / dist) * dash_speed)
        self.dash_duration = self.dash_duration_max
        self.dash_cooldown = self.dash_cooldown_max
        return True

    def get_dash_cooldown_ratio(self):
        """0.0 = ready, 1.0 = just used."""
        return self.dash_cooldown / self.dash_cooldown_max

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
        elif upgrade_key == "bullet_size":
            self.stats["bullet_size"] = round(self.stats["bullet_size"] + 0.3, 2)
            self.stats["damage"] = round(self.stats["damage"] + 0.5, 2)
            self.upgrade_counts["bullet_size"] += 1

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
        elif upgrade_key == "big_bullet_size":
            self.stats["bullet_size"] = round(self.stats["bullet_size"] + 0.8, 2)
            self.stats["damage"] = round(self.stats["damage"] + 1, 2)
            self.upgrade_counts["bullet_size"] += 3

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