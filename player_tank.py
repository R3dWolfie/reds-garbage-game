# player_tank.py
import pygame
from settings import *
from player_base import PlayerBase


class PlayerTank(PlayerBase):
    """The Juggernaut - high HP, rams enemies, slower but deals collision damage."""

    CLASS_KEY = "tank"
    DISPLAY_NAME = "Juggernaut"
    SPRITE_FILE = "player_tank.png"
    SPRITE_SIZE = (50, 50)
    SPRITE_COLOR = STEEL_BLUE

    BASE_STATS = {
        "speed": 3,
        "fire_rate": 80,
        "bullet_speed": 5,
        "max_health": 200,
        "multishot": 1,
        "damage": 1,
        "piercing": 1,
        "magnet": 0,
        "bullet_size": 1,
    }

    def __init__(self):
        super().__init__()
        self.collision_damage = 5  # Deals damage on contact
        self.ram_cooldown_max = 15  # Frames between ram hits

    def get_weapon_type(self):
        return "bullet"  # Also fires bullets, but slower

    def ram_enemy(self, enemy):
        """Deal collision damage to an enemy. Returns True if enemy died."""
        if self.collision_cooldown <= 0:
            total_dmg = self.collision_damage + (self.stats["damage"] // 2)
            dead = enemy.take_damage(total_dmg)
            self.collision_cooldown = self.ram_cooldown_max
            return dead
        return False

    def draw_ram_aura(self, surf):
        """Draw a faint aura showing the ram is active."""
        if self.collision_cooldown <= 0:
            aura_surf = pygame.Surface((self.rect.width + 20, self.rect.height + 20), pygame.SRCALPHA)
            pygame.draw.ellipse(aura_surf, (70, 130, 180, 50),
                                aura_surf.get_rect())
            surf.blit(aura_surf, (self.rect.x - 10, self.rect.y - 10))