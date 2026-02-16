# remote_ghosts.py
"""Multiplayer ghost sprites for remote players and enemies."""

import pygame
import math
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
        return 1 + self.max_health // 3

    def draw_health_bar(self, surf):
        if self.health >= self.max_health:
            return
        bw = self.rect.width
        bh = 5
        bx = self.rect.x
        by = self.rect.y - 8
        ratio = max(0, self.health / max(1, self.max_health))
        bc = GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        pygame.draw.rect(surf, DARK_GRAY, (bx, by, bw, bh))
        pygame.draw.rect(surf, bc, (bx, by, int(bw * ratio), bh))
        pygame.draw.rect(surf, WHITE, (bx, by, bw, bh), 1)


# Sprite map for all 6 classes
_SPRITE_MAP = {
    "default": ("player_default.png", (40, 40), GREEN, (57, 255, 20)),
    "tank":    ("player_tank.png",    (50, 50), STEEL_BLUE, (0, 150, 255)),
    "laser":   ("player_laser.png",   (40, 40), LASER_RED, (255, 50, 80)),
    "gunner":  ("player_default.png", (40, 40), (255, 165, 0), (255, 180, 50)),
    "sniper":  ("player_default.png", (40, 40), (200, 50, 255), (220, 100, 255)),
    "paladin": ("player_default.png", (40, 40), (255, 215, 0), (255, 230, 100)),
}


class RemotePlayerGhost(pygame.sprite.Sprite):
    """Visual representation of another player in multiplayer."""

    def __init__(self, player_id, class_key="default", username=None):
        super().__init__()
        self.player_id = player_id
        self.class_key = class_key
        self.username = username or f"Player{player_id}"
        self.target_x = 0
        self.target_y = 0
        self.level = 1
        self.health = 100
        self.max_health = 100
        self.is_dead = False
        self.equipped_hat = None
        self._hat_tick = 0
        self._build_sprite(class_key)

    def _build_sprite(self, class_key):
        fname, size, color, glow = _SPRITE_MAP.get(class_key, _SPRITE_MAP["default"])
        base = load_sprite(fname, size, color, size)
        self.image = make_neon_sprite(base, glow, glow_size=4)
        self.image.set_alpha(180)
        self.rect = self.image.get_rect()

    def update_from_state(self, state):
        self.target_x = state.get("x", self.target_x)
        self.target_y = state.get("y", self.target_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get("max_health", self.max_health)
        self.level = state.get("level", self.level)
        self.is_dead = state.get("is_dead", self.is_dead)
        if "username" in state:
            self.username = state["username"]
        if "equipped_hat" in state:
            self.equipped_hat = state["equipped_hat"]
        new_class = state.get("class", self.class_key)
        if new_class != self.class_key:
            self.class_key = new_class
            self._build_sprite(new_class)

    def update(self):
        self.rect.x += (self.target_x - self.rect.x) * 0.3
        self.rect.y += (self.target_y - self.rect.y) * 0.3

    def draw_label(self, surf):
        label = small_font.render(f"{self.username} Lv{self.level}", True, CYAN)
        surf.blit(label, (self.rect.centerx - label.get_width() // 2, self.rect.y - 18))

    def draw_hat(self, surf):
        """Draw equipped hat on remote player ghost."""
        if not self.equipped_hat:
            return
        hat_def = None
        for h in HAT_DEFS:
            if h["id"] == self.equipped_hat:
                hat_def = h; break
        if not hat_def or not hat_def.get("color"):
            return
        self._hat_tick += 1
        t = self._hat_tick
        cx = self.rect.centerx
        top = self.rect.top - 2
        c = hat_def["color"]
        hid = hat_def["id"]

        if hid == "catears":
            pygame.draw.polygon(surf, c, [(cx-12, top-2), (cx-14, top-14), (cx-4, top-2)])
            pygame.draw.polygon(surf, c, [(cx+4, top-2), (cx+14, top-14), (cx+12, top-2)])
        elif hid == "devilhorns":
            pygame.draw.line(surf, c, (cx-10, top), (cx-14, top-16), 3)
            pygame.draw.line(surf, c, (cx+10, top), (cx+14, top-16), 3)
        elif hid == "halo":
            fy = int(math.sin(t * 0.08) * 3)
            pygame.draw.ellipse(surf, (*c, 180), (cx-14, top-14+fy, 28, 8), 2)
        elif hid == "crown":
            pts = [(cx-12,top),(cx-12,top-8),(cx-8,top-4),(cx-4,top-10),
                   (cx,top-4),(cx+4,top-10),(cx+8,top-4),(cx+12,top-8),(cx+12,top)]
            pygame.draw.polygon(surf, c, pts)
        elif hid == "tophat":
            pygame.draw.rect(surf, c, (cx-16, top-2, 32, 5), border_radius=1)
            pygame.draw.rect(surf, c, (cx-10, top-18, 20, 18), border_radius=2)
        elif hid in ("wizard", "witchhat", "magichat"):
            pts = [(cx, top-22), (cx-14, top), (cx+14, top)]
            pygame.draw.polygon(surf, c, pts)
        elif hid in ("flamehat", "soulflame", "phoenixhat"):
            for i in range(-8, 10, 4):
                h2 = 8 + int(abs(math.sin(t*0.2+i*0.5))*8)
                pygame.draw.line(surf, c, (cx+i, top), (cx+i, top-h2), 2)
        elif hid == "omegahat":
            colors = [(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,200,255),(150,0,255)]
            for i, rc in enumerate(colors):
                pygame.draw.arc(surf, rc, (cx-14-i, top-14-i, 28+i*2, 10+i*2), 0, math.pi, 2)
        elif hid in ("stormhat", "thunderhelm"):
            pygame.draw.arc(surf, c, (cx-12, top-10, 24, 12), 0, math.pi, 3)
            if t % 20 < 4:
                pygame.draw.line(surf, (255,255,100), (cx-4, top-10), (cx-6, top+4), 2)
        elif hid == "icehat":
            pts = [(cx-10, top), (cx-6, top-12), (cx, top-6), (cx+6, top-12), (cx+10, top)]
            pygame.draw.polygon(surf, c, pts)
        elif hid == "voidhat":
            pygame.draw.circle(surf, (*c, 100), (cx, top-2), 8)
            pygame.draw.circle(surf, (40,0,60), (cx, top-2), 5)
        elif hid == "bunnyears":
            bounce = int(abs(math.sin(t * 0.06)) * 3)
            pygame.draw.ellipse(surf, c, (cx-12, top-20-bounce, 8, 22))
            pygame.draw.ellipse(surf, c, (cx+4, top-20-bounce, 8, 22))
        elif hid == "viking":
            pygame.draw.arc(surf, c, (cx-12, top-10, 24, 14), 0, math.pi, 3)
            pygame.draw.line(surf, c, (cx-12, top-4), (cx-18, top-16), 3)
            pygame.draw.line(surf, c, (cx+12, top-4), (cx+18, top-16), 3)
        elif hid == "cowboy":
            pygame.draw.rect(surf, c, (cx-18, top-2, 36, 5), border_radius=1)
            pygame.draw.arc(surf, c, (cx-12, top-14, 24, 14), 0, math.pi, 3)
        elif hid == "beret":
            pygame.draw.ellipse(surf, c, (cx-14, top-10, 28, 14))
        elif hid == "shadowhat":
            vs = pygame.Surface((32, 20), pygame.SRCALPHA)
            vs.fill((*c, 80))
            surf.blit(vs, (cx-16, top-12))
            ea = int(100 + abs(math.sin(t*0.1))*100)
            pygame.draw.circle(surf, (200,200,255,ea), (cx-5, top-4), 2)
            pygame.draw.circle(surf, (200,200,255,ea), (cx+5, top-4), 2)
        elif hid == "galaxyhat":
            pygame.draw.circle(surf, c, (cx, top-6), 10)
            for i in range(6):
                a = (i/6)*math.pi*2 + t*0.05
                sx = cx + int(7*math.cos(a))
                sy = (top-6) + int(7*math.sin(a))
                pygame.draw.circle(surf, (255,200,255), (sx, sy), 1)
        elif hid == "cosmichat":
            pygame.draw.circle(surf, c, (cx, top-6), 10)
            for ring in range(3):
                for i in range(6):
                    a = (i/6)*math.pi*2 + t*(0.04+ring*0.02)
                    rx = cx + int(12*math.cos(a))
                    ry = (top-8) + int(5*(ring*0.4+0.2)*math.sin(a))
                    pygame.draw.circle(surf, (*c, 120), (rx, ry), 1)
        elif hid == "glitchhat":
            seed = (t // 3) % 10
            for i in range(4):
                gx = cx - 10 + ((i*7+seed) % 18)
                gy = top - 10 + ((i*5+seed) % 8)
                gc = [(255,0,255),(0,255,255),(255,255,0),(255,0,100)][i]
                pygame.draw.rect(surf, (*gc, 160), (gx, gy, 5, 3))
        else:
            # Generic fallback
            pygame.draw.circle(surf, c, (cx, top-6), 6, 2)

    def draw_health_bar(self, surf):
        """Draw health bar above remote player."""
        if self.health >= self.max_health:
            return
        bw = self.rect.width + 10
        bh = 4
        bx = self.rect.centerx - bw // 2
        by = self.rect.y - 24
        ratio = max(0, self.health / max(1, self.max_health))
        pygame.draw.rect(surf, (30, 30, 40), (bx, by, bw, bh), border_radius=2)
        if ratio > 0:
            bc = (57, 255, 20) if ratio > 0.5 else ((255, 200, 50) if ratio > 0.25 else (255, 50, 50))
            pygame.draw.rect(surf, bc, (bx, by, int(bw * ratio), bh), border_radius=2)