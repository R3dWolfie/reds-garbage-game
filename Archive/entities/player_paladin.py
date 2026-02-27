# player_paladin.py
import pygame
import math
from core.settings import *
from entities.player_base import PlayerBase


class PlayerPaladin(PlayerBase):
    """The Paladin - self-healing aura, tanky, moderate damage. Heals nearby players in MP."""

    CLASS_KEY = "paladin"
    DISPLAY_NAME = "Paladin"
    SPRITE_FILE = "player_default.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = (255, 215, 0)  # Gold
    NEON_GLOW_COLOR = (255, 230, 100)

    BASE_STATS = {
        "speed": 3,
        "fire_rate": 50,
        "bullet_speed": 7,
        "max_health": 150,      # Very tanky
        "multishot": 1,
        "damage": 2,
        "piercing": 1,
        "magnet": 0,
        "bullet_size": 1.0,
        "xp_gain": 1.2,         # Bonus XP gain
        "accuracy": 1.0,
    }

    # Aura stats
    HEAL_PER_SEC = 2            # HP/sec self-heal
    HEAL_RADIUS = 200           # Pixels — heals nearby MP players
    HEAL_ALLIES_PER_SEC = 1     # HP/sec to nearby allies

    def __init__(self):
        super().__init__()
        self.heal_accum = 0.0
        self.aura_pulse = 0.0

    def update(self):
        super().update()
        # Self-heal aura
        self.heal_accum += self.HEAL_PER_SEC / FPS
        if self.heal_accum >= 1.0:
            amt = int(self.heal_accum)
            self.heal_accum -= amt
            if self.current_health < self.stats["max_health"]:
                self.current_health = min(self.stats["max_health"],
                                          self.current_health + amt)
        self.aura_pulse += 0.05

    def draw_heal_aura(self, surf):
        """Draw golden healing aura ring."""
        pulse = math.sin(self.aura_pulse) * 0.3 + 0.7
        r = int(self.HEAL_RADIUS * pulse * 0.3)  # Visual ring smaller than actual
        aura = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(aura, (255, 215, 0, int(15 * pulse)), (r+2, r+2), r)
        pygame.draw.circle(aura, (255, 230, 100, int(30 * pulse)), (r+2, r+2), r, 2)
        surf.blit(aura, (self.rect.centerx - r - 2, self.rect.centery - r - 2))

    def get_weapon_type(self):
        return "bullet"

    def get_bullet_color(self):
        return (255, 215, 0)  # Gold