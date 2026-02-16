# remote_ghosts.py
"""Multiplayer ghost sprites for remote players and enemies."""

import pygame
from core.settings import *
from core.sprite_loader import load_sprite, make_neon_sprite
from core.game_state import small_font


class RemoteEnemyGhost(pygame.sprite.Sprite):
    """Client-side mirror of a host's enemy. No AI, just visual tracking."""

    def __init__(self, enemy_id, x, y, is_boss=False, wave=1):
        super().__init__()
        self.enemy_id = enemy_id
        self.is_boss = is_boss
        self.target_x = x
        self.target_y = y
        self.max_health = 1
        self.health = 1
        self.damage = 25 if is_boss else 10

        size = (50, 50) if is_boss else (30, 30)
        color = PURPLE if is_boss else RED
        glow_color = (180, 0, 255) if is_boss else (255, 30, 60)
        fname = "boss.png" if is_boss else "enemy_basic.png"
        base = load_sprite(fname, size, color, size)
        self.image = make_neon_sprite(base, glow_color, glow_size=4 if is_boss else 3)
        self.image.set_alpha(200)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update_from_state(self, state):
        self.target_x = state.get("x", self.target_x)
        self.target_y = state.get("y", self.target_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get("max_health", self.max_health)

    def update(self):
        self.rect.x += (self.target_x - self.rect.x) * 0.4
        self.rect.y += (self.target_y - self.rect.y) * 0.4

    def take_damage(self, amount):
        pass

    def get_xp_drop_count(self):
        base = 1
        bonus = self.max_health // 3
        return base + bonus

    def draw_health_bar(self, surf):
        if self.health >= self.max_health:
            return
        bar_width = self.rect.width
        bar_height = 5
        bar_x = self.rect.x
        bar_y = self.rect.y - 8
        hp_ratio = max(0, self.health / max(1, self.max_health))
        if hp_ratio > 0.5:
            color = GREEN
        elif hp_ratio > 0.25:
            color = YELLOW
        else:
            color = RED
        pygame.draw.rect(surf, DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(surf, color, (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(surf, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)


class RemotePlayerGhost(pygame.sprite.Sprite):
    """Visual representation of another player in multiplayer."""

    def __init__(self, player_id, class_key="default", username=None):
        super().__init__()
        info = CLASS_INFO.get(class_key, CLASS_INFO["default"])
        self.player_id = player_id
        self.class_key = class_key
        self.username = username or f"Player{player_id}"
        self.target_x = 0
        self.target_y = 0
        self.level = 1
        self.health = 100

        sprite_map = {
            "default": ("player_default.png", (40, 40), GREEN, (57, 255, 20)),
            "tank": ("player_tank.png", (50, 50), STEEL_BLUE, (0, 150, 255)),
            "laser": ("player_laser.png", (40, 40), LASER_RED, (255, 50, 80)),
        }
        fname, size, color, glow = sprite_map.get(class_key, sprite_map["default"])
        base = load_sprite(fname, size, color, size)
        self.image = make_neon_sprite(base, glow, glow_size=4)
        self.image.set_alpha(180)
        self.rect = self.image.get_rect()

    def update_from_state(self, state):
        self.target_x = state.get("x", self.target_x)
        self.target_y = state.get("y", self.target_y)
        self.health = state.get("health", self.health)
        self.level = state.get("level", self.level)
        if "username" in state:
            self.username = state["username"]

        new_class = state.get("class", self.class_key)
        if new_class != self.class_key:
            self.class_key = new_class
            sprite_map = {
                "default": ("player_default.png", (40, 40), GREEN, (57, 255, 20)),
                "tank": ("player_tank.png", (50, 50), STEEL_BLUE, (0, 150, 255)),
                "laser": ("player_laser.png", (40, 40), LASER_RED, (255, 50, 80)),
            }
            fname, size, color, glow = sprite_map.get(new_class, sprite_map["default"])
            base = load_sprite(fname, size, color, size)
            self.image = make_neon_sprite(base, glow, glow_size=4)
            self.image.set_alpha(180)
            self.rect = self.image.get_rect()

    def update(self):
        self.rect.x += (self.target_x - self.rect.x) * 0.3
        self.rect.y += (self.target_y - self.rect.y) * 0.3

    def draw_label(self, surf):
        label = small_font.render(f"{self.username} Lv{self.level}", True, CYAN)
        surf.blit(label, (self.rect.centerx - label.get_width() // 2, self.rect.y - 18))