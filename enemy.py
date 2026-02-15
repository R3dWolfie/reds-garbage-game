# enemy.py
import pygame
import random
import math
from settings import *
from sprite_loader import load_sprite


class Enemy(pygame.sprite.Sprite):
    def __init__(self, player, wave):
        super().__init__()
        self.player = player
        self.is_boss = False

        self.image = load_sprite("enemy_basic.png", (30, 30), RED, (30, 30))
        self.rect = self.image.get_rect()

        self.max_health = 1 + (wave // 3)
        self.health = self.max_health
        self.speed = 2 + (wave * 0.1)
        self.damage = 10

        self._spawn_at_edge()

    def _spawn_at_edge(self):
        sw = SCREEN_WIDTH
        sh = SCREEN_HEIGHT
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top':
            self.rect.x = random.randint(0, sw)
            self.rect.y = -40
        elif side == 'bottom':
            self.rect.x = random.randint(0, sw)
            self.rect.y = sh + 40
        elif side == 'left':
            self.rect.x = -40
            self.rect.y = random.randint(0, sh)
        elif side == 'right':
            self.rect.x = sw + 40
            self.rect.y = random.randint(0, sh)

    def get_xp_drop_count(self):
        """More HP = more XP gems dropped."""
        base = 1
        bonus = self.max_health // 3
        return base + bonus

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.kill()
            return True
        return False

    def draw_health_bar(self, surf):
        if self.health >= self.max_health:
            return

        bar_width = self.rect.width
        bar_height = 5
        bar_x = self.rect.x
        bar_y = self.rect.y - 8

        hp_ratio = max(0, self.health / self.max_health)

        if hp_ratio > 0.5:
            color = GREEN
        elif hp_ratio > 0.25:
            color = YELLOW
        else:
            color = RED

        pygame.draw.rect(surf, DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(surf, color, (bar_x, bar_y, bar_width * hp_ratio, bar_height))
        pygame.draw.rect(surf, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    def update(self):
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)

        if dist != 0:
            dx, dy = dx / dist, dy / dist
            self.rect.x += dx * self.speed
            self.rect.y += dy * self.speed


class Boss(Enemy):
    def __init__(self, player, wave):
        super().__init__(player, wave)
        self.is_boss = True

        self.image = load_sprite("enemy_boss.png", (80, 80), PURPLE, (80, 80))
        self.rect = self.image.get_rect()
        self._spawn_at_edge()

        self.max_health = 20 + (wave * 5)
        self.health = self.max_health
        self.speed = 1.5 + (wave * 0.05)
        self.damage = 25

    def get_xp_drop_count(self):
        return 10 + (self.max_health // 5)

    def draw_health_bar(self, surf):
        bar_width = self.rect.width + 20
        bar_height = 8
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.y - 12

        hp_ratio = max(0, self.health / self.max_health)

        if hp_ratio > 0.5:
            color = GREEN
        elif hp_ratio > 0.25:
            color = YELLOW
        else:
            color = RED

        pygame.draw.rect(surf, DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(surf, color, (bar_x, bar_y, bar_width * hp_ratio, bar_height))
        pygame.draw.rect(surf, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)
