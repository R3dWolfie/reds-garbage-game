# remote_ghosts.py
"""Multiplayer ghost sprites for remote players and enemies.
Optimized for smooth interpolation with high-frequency network updates.
Includes per-player magnet radius visualization."""

import pygame
import math
import time
import random
from core.settings import *
from core.sprite_loader import load_sprite, make_neon_sprite
import core.game_state as _gs

# Per-player magnet colors — soft, distinct, non-clashing
# Index by player_id % len to cycle
_MAGNET_PALETTE = [
    (0, 220, 255),    # Cyan (local player keeps this)
    (255, 120, 255),  # Pink
    (255, 200, 60),   # Gold
    (120, 255, 120),  # Lime
    (255, 140, 80),   # Coral
    (180, 140, 255),  # Lavender
    (80, 255, 200),   # Mint
    (255, 100, 100),  # Soft red
]


def _get_player_magnet_color(player_id):
    """Get a unique magnet color for a player."""
    return _MAGNET_PALETTE[player_id % len(_MAGNET_PALETTE)]


class RemoteEnemyGhost(pygame.sprite.Sprite):
    """Client-side mirror of a host's enemy. No AI, just visual tracking."""

    ENEMY_VISUALS = {
        "basic":       ((255, 30, 60),   (255, 30, 60),   (30, 30), "enemy_basic.png"),
        "arrow":       ((180, 0, 255),   (180, 0, 255),   (30, 15), "enemy_arrow.png"),
        "tank":        ((255, 140, 0),   (255, 140, 0),   (45, 45), "enemy_tank.png"),
        "splitter":    ((0, 255, 100),   (0, 255, 100),   (35, 35), "enemy_basic.png"),
        "zigzag":      ((255, 255, 0),   (255, 255, 0),   (28, 28), "enemy_zigzag.png"),
        "teleport":    ((200, 100, 255), (200, 100, 255), (30, 30), "enemy_basic.png"),
        "shield":      ((0, 200, 255),   (0, 200, 255),   (35, 35), "enemy_basic.png"),
        "swarm":       ((255, 150, 50),  (255, 150, 50),  (18, 18), "enemy_basic.png"),
        "vortex":      ((100, 0, 200),   (150, 50, 255),  (35, 35), "enemy_basic.png"),
        "necro":       ((0, 180, 0),     (0, 255, 0),     (35, 35), "enemy_basic.png"),
        "spiral":      ((255, 0, 128),   (255, 50, 150),  (30, 30), "enemy_basic.png"),
        "mine_layer":  ((200, 200, 0),   (255, 255, 0),   (30, 30), "enemy_basic.png"),
        "laser_drone": ((0, 255, 255),   (0, 255, 255),   (28, 28), "enemy_basic.png"),
        "leech_priest":((150, 0, 50),    (200, 0, 80),    (35, 35), "enemy_basic.png"),
        "phase_wraith":((180, 180, 255), (200, 200, 255), (32, 32), "enemy_basic.png"),
        "charger_bull":((200, 50, 0),    (255, 80, 0),    (40, 40), "enemy_basic.png"),
        "mimic":       ((255, 215, 0),   (255, 230, 50),  (30, 30), "enemy_basic.png"),
        "orbiter":     ((100, 200, 255), (130, 220, 255), (30, 30), "enemy_basic.png"),
        "sniper":      ((255, 50, 50),   (255, 80, 80),   (28, 28), "enemy_basic.png"),
        "parasite":    ((0, 200, 100),   (0, 255, 130),   (25, 25), "enemy_basic.png"),
        "shadow_shade":((80, 0, 120),    (120, 0, 180),   (30, 30), "enemy_basic.png"),
        "omega_drone": ((255, 255, 255), (200, 200, 255), (30, 30), "enemy_basic.png"),
    }

    def __init__(self, enemy_id, x, y, is_boss=False, wave=1, etype=None, speed=None):
        super().__init__()
        self.enemy_id = enemy_id
        self.is_boss = is_boss
        self.etype = etype
        self.target_x = float(x)
        self.target_y = float(y)
        self.max_health = 1
        self.health = 1
        self.damage = 25 if is_boss else 10
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._last_update = time.monotonic()

        if is_boss:
            size, color, glow_color, fname = (50, 50), PURPLE, (180, 0, 255), "boss.png"
        elif etype and etype in self.ENEMY_VISUALS:
            color, glow_color, size, fname = self.ENEMY_VISUALS[etype]
        else:
            size, color, glow_color, fname = (30, 30), RED, (255, 30, 60), "enemy_basic.png"

        base = load_sprite(fname, size, color, size)
        self.image = make_neon_sprite(base, glow_color, glow_size=4 if is_boss else 3)
        self.image.set_alpha(200)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update_from_state(self, state):
        new_x = state.get("x", self.target_x)
        new_y = state.get("y", self.target_y)
        now = time.monotonic()
        dt = max(0.016, now - self._last_update)
        self._last_update = now
        self._vel_x = (new_x - self.target_x) / dt
        self._vel_y = (new_y - self.target_y) / dt
        self.target_x = float(new_x)
        self.target_y = float(new_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get("max_health", self.max_health)

    def update(self):
        now = time.monotonic()
        elapsed = min(now - self._last_update, 0.15)
        pred_x = self.target_x + self._vel_x * elapsed
        pred_y = self.target_y + self._vel_y * elapsed
        dx = pred_x - self.rect.x
        dy = pred_y - self.rect.y
        dist_sq = dx*dx + dy*dy
        if dist_sq < 4:
            self.rect.x = int(pred_x)
            self.rect.y = int(pred_y)
        else:
            self.rect.x = int(self.rect.x + dx * 0.35)
            self.rect.y = int(self.rect.y + dy * 0.35)

    def take_damage(self, amount):
        pass

    def get_xp_drop_count(self):
        return 1 + self.max_health // 3

    def draw_health_bar(self, surf):
        if self.health >= self.max_health:
            return
        bw = self.rect.width
        bx, by = self.rect.x, self.rect.y - 8
        ratio = max(0, self.health / max(1, self.max_health))
        bc = GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        pygame.draw.rect(surf, DARK_GRAY, (bx, by, bw, 5))
        pygame.draw.rect(surf, bc, (bx, by, int(bw * ratio), 5))
        pygame.draw.rect(surf, WHITE, (bx, by, bw, 5), 1)


_SPRITE_MAP = {
    "default": ("player_default.png", (40, 40), GREEN, (57, 255, 20)),
    "tank":    ("player_tank.png",    (50, 50), STEEL_BLUE, (0, 150, 255)),
    "laser":   ("player_laser.png",   (40, 40), LASER_RED, (255, 50, 80)),
    "gunner":  ("player_default.png", (40, 40), (255, 165, 0), (255, 180, 50)),
    "sniper":  ("player_default.png", (40, 40), (200, 50, 255), (220, 100, 255)),
    "paladin": ("player_default.png", (40, 40), (255, 215, 0), (255, 230, 100)),
}


class RemotePlayerGhost(pygame.sprite.Sprite):
    """Visual representation of another player in multiplayer.
    Uses time-based interpolation for smooth movement.
    Includes magnet radius visualization."""

    def __init__(self, player_id, class_key="default", username=None):
        super().__init__()
        self.player_id = player_id
        self.class_key = class_key
        self.username = username or f"Player{player_id}"
        self.target_x = 0.0
        self.target_y = 0.0
        self.level = 1
        self.health = 100
        self.max_health = 100
        self.is_dead = False
        self.equipped_hat = None
        self.magnet_radius = 0
        self._hat_tick = 0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._last_update = time.monotonic()
        self._magnet_color = _get_player_magnet_color(player_id)
        self._magnet_tick = random.randint(0, 1000)  # Offset so they don't all pulse in sync
        self._magnet_ring_cache = None
        self._magnet_ring_radius = 0
        self._build_sprite(class_key)

    def _build_sprite(self, class_key):
        fname, size, color, glow = _SPRITE_MAP.get(class_key, _SPRITE_MAP["default"])
        base = load_sprite(fname, size, color, size)
        self.image = make_neon_sprite(base, glow, glow_size=4)
        self.image.set_alpha(180)
        self.rect = self.image.get_rect()

    def update_from_state(self, state):
        new_x = state.get("x", self.target_x)
        new_y = state.get("y", self.target_y)
        now = time.monotonic()
        dt = max(0.016, now - self._last_update)
        self._last_update = now
        self._vel_x = (new_x - self.target_x) / dt
        self._vel_y = (new_y - self.target_y) / dt
        self.target_x = float(new_x)
        self.target_y = float(new_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get("max_health", self.max_health)
        self.level = state.get("level", self.level)
        self.is_dead = state.get("is_dead", self.is_dead)
        if "username" in state:
            self.username = state["username"]
        if "equipped_hat" in state:
            self.equipped_hat = state["equipped_hat"]
        if "magnet_r" in state:
            self.magnet_radius = state["magnet_r"]
        new_class = state.get("class", self.class_key)
        if new_class != self.class_key:
            self.class_key = new_class
            self._build_sprite(new_class)

    def update(self):
        now = time.monotonic()
        elapsed = min(now - self._last_update, 0.15)
        pred_x = self.target_x + self._vel_x * elapsed
        pred_y = self.target_y + self._vel_y * elapsed
        dx = pred_x - self.rect.x
        dy = pred_y - self.rect.y
        dist_sq = dx*dx + dy*dy
        if dist_sq < 4:
            self.rect.x = int(pred_x)
            self.rect.y = int(pred_y)
        else:
            self.rect.x = int(self.rect.x + dx * 0.4)
            self.rect.y = int(self.rect.y + dy * 0.4)
        self._magnet_tick += 1

    def draw_magnet(self, surf, gem_groups=None):
        """Draw magnet radius and pull-line particles.

        Uses orbiting dots along the ring edge instead of a full circle,
        so multiple players' magnets don't overlap into ugly blobs.
        Animated pull lines show gems being attracted.
        """
        radius = self.magnet_radius
        if radius <= 0:
            return
        cx, cy = self.rect.centerx, self.rect.centery
        mc = self._magnet_color
        t = self._magnet_tick

        # ── Orbiting dots along the ring edge (6-10 dots depending on radius)
        num_dots = max(6, min(12, radius // 20))
        base_alpha = 50 + int(25 * math.sin(t * 0.06))  # Gentle pulse
        for i in range(num_dots):
            angle = (i / num_dots) * math.pi * 2 + t * 0.02
            dx = int(math.cos(angle) * radius)
            dy = int(math.sin(angle) * radius)
            # Size pulses slightly per dot
            dot_sz = 2 + int(abs(math.sin(angle + t * 0.05)))
            pygame.draw.circle(surf, mc, (cx + dx, cy + dy), dot_sz)

        # ── Faint dashed ring (only every other segment, very subtle)
        seg_count = max(8, radius // 12)
        for i in range(seg_count):
            if i % 3 != 0:  # Skip 2/3 of segments = dashed look
                continue
            a1 = (i / seg_count) * math.pi * 2 + t * 0.015
            a2 = ((i + 1) / seg_count) * math.pi * 2 + t * 0.015
            p1 = (cx + int(math.cos(a1) * radius), cy + int(math.sin(a1) * radius))
            p2 = (cx + int(math.cos(a2) * radius), cy + int(math.sin(a2) * radius))
            pygame.draw.line(surf, (*mc, base_alpha) if len(mc) == 3 else mc, p1, p2, 1)

        # ── Pull lines: draw small animated streaks toward pulled gems
        if gem_groups:
            max_lines = 8  # Cap to prevent overdraw
            lines_drawn = 0
            for grp in gem_groups:
                for gem in grp:
                    if lines_drawn >= max_lines:
                        break
                    gx, gy = gem.rect.centerx, gem.rect.centery
                    dist = math.hypot(gx - cx, gy - cy)
                    if 10 < dist <= radius:
                        lines_drawn += 1
                        # Animated dash: a short streak moving from gem toward player
                        # The streak position oscillates along the pull direction
                        pull_frac = 1.0 - (dist / radius)  # 0 at edge, 1 at center
                        # Streak travels from gem toward player
                        streak_t = ((t * 3 + hash(id(gem))) % 60) / 60.0  # 0..1 cycle
                        # Position along the line from gem to player
                        sx = gx + (cx - gx) * streak_t
                        sy = gy + (cy - gy) * streak_t
                        # Short line segment in the pull direction
                        seg_len = 6 + int(pull_frac * 4)
                        dx_n = (cx - gx) / dist
                        dy_n = (cy - gy) / dist
                        ex = sx + dx_n * seg_len
                        ey = sy + dy_n * seg_len
                        # Fade based on distance: closer = brighter
                        alpha_mult = 0.3 + pull_frac * 0.5
                        line_c = (
                            int(mc[0] * alpha_mult),
                            int(mc[1] * alpha_mult),
                            int(mc[2] * alpha_mult),
                        )
                        pygame.draw.line(surf, line_c, (int(sx), int(sy)), (int(ex), int(ey)), 1)
                if lines_drawn >= max_lines:
                    break

    def draw_label(self, surf):
        label = _gs.small_font.render(f"{self.username} Lv{self.level}", True, CYAN)
        surf.blit(label, (self.rect.centerx - label.get_width() // 2, self.rect.y - 18))

    def draw_hat(self, surf):
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
            pts = [(cx-12,top),(cx-12,top-8),(cx-8,top-4),(cx-4,top-10),(cx,top-4),(cx+4,top-10),(cx+8,top-4),(cx+12,top-8),(cx+12,top)]
            pygame.draw.polygon(surf, c, pts)
        elif hid == "tophat":
            pygame.draw.rect(surf, c, (cx-16, top-2, 32, 5), border_radius=1)
            pygame.draw.rect(surf, c, (cx-10, top-18, 20, 18), border_radius=2)
        elif hid in ("wizard", "witchhat", "magichat"):
            pygame.draw.polygon(surf, c, [(cx, top-22), (cx-14, top), (cx+14, top)])
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
            pygame.draw.polygon(surf, c, [(cx-10, top), (cx-6, top-12), (cx, top-6), (cx+6, top-12), (cx+10, top)])
        elif hid == "voidhat":
            pygame.draw.circle(surf, c, (cx, top-2), 8)
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
            pygame.draw.rect(surf, c, (cx-16, top-12, 32, 20))
            pygame.draw.circle(surf, (200,200,255), (cx-5, top-4), 2)
            pygame.draw.circle(surf, (200,200,255), (cx+5, top-4), 2)
        elif hid == "galaxyhat":
            pygame.draw.circle(surf, c, (cx, top-6), 10)
            for i in range(6):
                a = (i/6)*math.pi*2 + t*0.05
                pygame.draw.circle(surf, (255,200,255), (cx + int(7*math.cos(a)), (top-6) + int(7*math.sin(a))), 1)
        elif hid == "cosmichat":
            pygame.draw.circle(surf, c, (cx, top-6), 10)
            for ring in range(3):
                for i in range(6):
                    a = (i/6)*math.pi*2 + t*(0.04+ring*0.02)
                    pygame.draw.circle(surf, c, (cx + int(12*math.cos(a)), (top-8) + int(5*(ring*0.4+0.2)*math.sin(a))), 1)
        elif hid == "glitchhat":
            seed = (t // 3) % 10
            for i in range(4):
                gx = cx - 10 + ((i*7+seed) % 18)
                gy = top - 10 + ((i*5+seed) % 8)
                gc = [(255,0,255),(0,255,255),(255,255,0),(255,0,100)][i]
                pygame.draw.rect(surf, gc, (gx, gy, 5, 3))
        else:
            pygame.draw.circle(surf, c, (cx, top-6), 6, 2)

    def draw_health_bar(self, surf):
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