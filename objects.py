# objects.py
import pygame
import math
from settings import *
from sprite_loader import load_sprite


class Bullet(pygame.sprite.Sprite):
    def __init__(self, start_pos, target_pos, speed, piercing=1, size=1.0):
        super().__init__()
        base = max(4, int(10 * size))
        self.image = load_sprite("bullet.png", (base, base), YELLOW, (base, base))
        self.rect = self.image.get_rect()
        self.rect.center = start_pos

        self.piercing = piercing
        self.hits = 0
        self.hit_enemies = []

        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.dx = (dx / dist) * speed
        self.dy = (dy / dist) * speed

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


class LaserBeam(pygame.sprite.Sprite):
    """Slow, wide beam that pierces everything. Used by Arcanist class."""

    def __init__(self, start_pos, target_pos, speed, piercing=999, size=1.0):
        super().__init__()
        w = max(8, int(20 * size))
        h = max(4, int(8 * size))
        self.image = load_sprite("laser_beam.png", (w, h), LASER_RED, (w, h))
        self.rect = self.image.get_rect()
        self.rect.center = start_pos

        self.piercing = piercing
        self.hits = 0
        self.hit_enemies = []
        self.lifetime = 300  # Frames before it dies

        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.dx = (dx / dist) * speed
        self.dy = (dy / dist) * speed

        # Rotate sprite to face direction
        angle = math.degrees(math.atan2(-dy, dx))
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=self.rect.center)

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


class ExpGem(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = load_sprite("xp_gem.png", (10, 15), CYAN, (10, 15))
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.speed = 0  # For magnet pull

    def move_toward(self, target_pos, pull_speed):
        """Move toward a target (for magnet effect)."""
        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0 and dist < 5:
            # Close enough, snap
            self.rect.center = target_pos
        elif dist > 0:
            self.rect.x += (dx / dist) * pull_speed
            self.rect.y += (dy / dist) * pull_speed


class HealthOrb(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = load_sprite("health_orb.png", (12, 12), PINK, (12, 12))
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.heal_amount = HEALTH_ORB_HEAL