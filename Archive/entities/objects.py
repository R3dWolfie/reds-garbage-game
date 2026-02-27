# objects.py
import pygame
import math
import random
from core.settings import *
from core.settings import get_dt
from core.sprite_loader import load_sprite


_bullet_cache = {}  # Cache: (size, color_tuple) -> Surface

def _get_bullet_surface(size, color):
    """Get or create a cached bullet surface."""
    size = min(3.0, size)  # Hard cap
    # Quantize size to reduce cache entries (round to 0.25)
    qsize = round(size * 4) / 4
    key = (qsize, color)
    if key not in _bullet_cache:
        bullet_size = int(10 * qsize)
        total = bullet_size + 6
        surf = pygame.Surface((total, total), pygame.SRCALPHA)
        c = color or (255, 255, 0)
        bright = (min(255, c[0]+80), min(255, c[1]+80), min(255, c[2]+80))
        core_c = (min(255, c[0]+160), min(255, c[1]+160), min(255, c[2]+160))
        pygame.draw.circle(surf, (*c, 40), (total // 2, total // 2), total // 2)
        pygame.draw.circle(surf, bright, (total // 2, total // 2), bullet_size // 2)
        pygame.draw.circle(surf, core_c, (total // 2, total // 2), max(1, bullet_size // 4))
        _bullet_cache[key] = surf
    return _bullet_cache[key]


class Bullet(pygame.sprite.Sprite):
    def __init__(self, start_pos, target_pos, speed, piercing=1, size=1.0, bounces=0, color=None):
        super().__init__()
        size = min(3.0, size)  # Hard cap
        c = color or (255, 255, 0)
        self.image = _get_bullet_surface(size, c)
        self.rect = self.image.get_rect()
        self.rect.center = start_pos

        self.piercing = piercing
        self.hits = 0
        self.hit_enemies = set()  # Use set for O(1) lookup
        self.bounces_left = bounces

        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.dx = (dx / dist) * speed
        self.dy = (dy / dist) * speed

    def update(self):
        self.rect.x += self.dx * get_dt()
        self.rect.y += self.dy * get_dt()
        screen_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        if not screen_rect.colliderect(self.rect):
            if self.bounces_left > 0:
                self.bounces_left -= 1
                # Bounce off edges
                if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
                    self.dx = -self.dx
                if self.rect.top < 0 or self.rect.bottom > SCREEN_HEIGHT:
                    self.dy = -self.dy
                self.rect.clamp_ip(screen_rect)
                self.hit_enemies.clear()  # Can re-hit after bounce
            else:
                self.kill()


_enemy_proj_surface = None

class EnemyProjectile(pygame.sprite.Sprite):
    """Red projectile shot by Tank enemies toward players."""

    def __init__(self, start_pos, target_pos, speed=4):
        super().__init__()
        global _enemy_proj_surface
        if _enemy_proj_surface is None:
            _enemy_proj_surface = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(_enemy_proj_surface, (255, 30, 60, 40), (7, 7), 7)
            pygame.draw.circle(_enemy_proj_surface, (255, 50, 80), (7, 7), 5)
            pygame.draw.circle(_enemy_proj_surface, (255, 150, 170), (7, 7), 2)
        self.image = _enemy_proj_surface
        self.rect = self.image.get_rect()
        self.rect.center = start_pos

        self.damage = 10

        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.dx = (dx / dist) * speed
        self.dy = (dy / dist) * speed

    def update(self):
        _d = get_dt()
        self.rect.x += self.dx * _d
        self.rect.y += self.dy * _d
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


class LaserBeam(pygame.sprite.Sprite):
    """Slow, wide beam that pierces everything. Used by Arcanist class."""

    def __init__(self, start_pos, target_pos, speed, piercing=999, size=1.0):
        super().__init__()
        beam_width = int(20 * size)
        beam_height = int(8 * size)
        # Neon laser beam
        total_w = beam_width + 6
        total_h = beam_height + 6
        base_img = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
        # Outer glow
        pygame.draw.rect(base_img, (255, 50, 50, 30), (0, 0, total_w, total_h))
        # Inner beam
        pygame.draw.rect(base_img, (255, 80, 80), (3, 3, beam_width, beam_height))
        # Bright core
        pygame.draw.rect(base_img, (255, 180, 180), (3 + beam_width // 4, 3 + beam_height // 4,
                                                       beam_width // 2, beam_height // 2))
        self.image = base_img
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
        self.rect.x += self.dx * get_dt()
        self.rect.y += self.dy * get_dt()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


_gem_surface = None
_mega_gem_surface = None
_ultra_gem_surface = None

def _get_gem_surface():
    """Small cyan gem (1 xp)"""
    global _gem_surface
    if _gem_surface is None:
        _gem_surface = pygame.Surface((16, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(_gem_surface, (0, 255, 255, 30), (0, 0, 16, 20))
        points = [(8, 1), (14, 10), (8, 19), (2, 10)]
        pygame.draw.polygon(_gem_surface, (0, 220, 255), points)
        pygame.draw.polygon(_gem_surface, (150, 255, 255), points, 1)
        pygame.draw.polygon(_gem_surface, (200, 255, 255), [(8, 5), (11, 10), (8, 15), (5, 10)])
    return _gem_surface

def _get_mega_gem_surface():
    """Red gem (10+ xp) - condensed from 10 cyan gems"""
    global _mega_gem_surface
    if _mega_gem_surface is None:
        _mega_gem_surface = pygame.Surface((24, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(_mega_gem_surface, (255, 50, 50, 40), (0, 0, 24, 30))
        points = [(12, 1), (22, 15), (12, 29), (2, 15)]
        pygame.draw.polygon(_mega_gem_surface, (255, 60, 60), points)
        pygame.draw.polygon(_mega_gem_surface, (255, 150, 150), points, 2)
        pygame.draw.polygon(_mega_gem_surface, (255, 200, 200), [(12, 7), (17, 15), (12, 23), (7, 15)])
    return _mega_gem_surface

def _get_ultra_gem_surface():
    """Green gem (100+ xp) - condensed from 10 red gems"""
    global _ultra_gem_surface
    if _ultra_gem_surface is None:
        _ultra_gem_surface = pygame.Surface((32, 38), pygame.SRCALPHA)
        pygame.draw.ellipse(_ultra_gem_surface, (50, 255, 50, 50), (0, 0, 32, 38))
        points = [(16, 1), (30, 19), (16, 37), (2, 19)]
        pygame.draw.polygon(_ultra_gem_surface, (40, 220, 40), points)
        pygame.draw.polygon(_ultra_gem_surface, (100, 255, 100), points, 2)
        pygame.draw.polygon(_ultra_gem_surface, (180, 255, 180), [(16, 9), (23, 19), (16, 29), (9, 19)])
        # Inner sparkle
        pygame.draw.circle(_ultra_gem_surface, (200, 255, 200), (16, 19), 4)
    return _ultra_gem_surface


class ExpGem(pygame.sprite.Sprite):
    def __init__(self, pos, xp_value=1):
        super().__init__()
        self.xp_value = xp_value
        self._gem_tier = 0
        if xp_value >= 100:
            self.image = _get_ultra_gem_surface()
            self._gem_tier = 2
        elif xp_value >= 10:
            self.image = _get_mega_gem_surface()
            self._gem_tier = 1
        else:
            self.image = _get_gem_surface()
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.speed = 0
        self.spawn_time = pygame.time.get_ticks()
        self._alpha = 255

    def move_toward(self, target_pos, pull_speed):
        """Move toward a target (for magnet effect)."""
        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0 and dist < 5:
            self.rect.center = target_pos
        elif dist > 0:
            self.rect.x += (dx / dist) * pull_speed
            self.rect.y += (dy / dist) * pull_speed

    def update(self):
        """Fade and despawn after 15 seconds."""
        age_ms = pygame.time.get_ticks() - self.spawn_time
        if age_ms > 13000:  # Start fading at 13s
            fade_ratio = max(0, 1.0 - (age_ms - 13000) / 2000.0)
            self._alpha = int(255 * fade_ratio)
            if self._alpha <= 0:
                self.kill()
                return
            if self._gem_tier >= 2:
                base = _get_ultra_gem_surface()
            elif self._gem_tier >= 1 or self.xp_value >= 10:
                base = _get_mega_gem_surface()
            else:
                base = _get_gem_surface()
            if self._alpha < 250:
                faded = base.copy()
                faded.set_alpha(self._alpha)
                self.image = faded


_health_orb_surface = None

class HealthOrb(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        global _health_orb_surface
        if _health_orb_surface is None:
            _health_orb_surface = pygame.Surface((18, 18), pygame.SRCALPHA)
            pygame.draw.circle(_health_orb_surface, (255, 100, 200, 30), (9, 9), 9)
            pygame.draw.circle(_health_orb_surface, (255, 80, 180), (9, 9), 6)
            pygame.draw.circle(_health_orb_surface, (255, 200, 230), (9, 9), 3)
            pygame.draw.line(_health_orb_surface, WHITE, (7, 9), (11, 9), 2)
            pygame.draw.line(_health_orb_surface, WHITE, (9, 7), (9, 11), 2)
        self.image = _health_orb_surface
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.heal_amount = HEALTH_ORB_HEAL
        self.spawn_time = pygame.time.get_ticks()

    def move_toward(self, target_pos, pull_speed):
        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0 and dist < 5:
            self.rect.center = target_pos
        elif dist > 0:
            self.rect.x += (dx / dist) * pull_speed
            self.rect.y += (dy / dist) * pull_speed


_gold_coin_surface = None

class GoldCoin(pygame.sprite.Sprite):
    """Gold coin that drops from enemies - used for permanent shop upgrades."""

    def __init__(self, pos, value=1):
        super().__init__()
        global _gold_coin_surface
        if _gold_coin_surface is None:
            _gold_coin_surface = pygame.Surface((18, 18), pygame.SRCALPHA)
            pygame.draw.circle(_gold_coin_surface, (255, 215, 0, 30), (9, 9), 9)
            pygame.draw.circle(_gold_coin_surface, (255, 200, 0), (9, 9), 7)
            pygame.draw.circle(_gold_coin_surface, (255, 240, 100), (9, 9), 4)
            pygame.draw.circle(_gold_coin_surface, (255, 215, 0), (9, 9), 7, 2)
        self.image = _gold_coin_surface
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.value = value
        self.speed = 0
        self.spawn_time = pygame.time.get_ticks()

    def move_toward(self, target_pos, pull_speed):
        """Move toward a target (for magnet effect)."""
        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0 and dist < 5:
            self.rect.center = target_pos
        elif dist > 0:
            self.rect.x += (dx / dist) * pull_speed
            self.rect.y += (dy / dist) * pull_speed


class XPRoomba(pygame.sprite.Sprite):
    """Autonomous roomba that roams the area hunting XP gems and gold coins.
    Invincible to enemies — they pass right through it."""

    STATE_WANDER = 0
    STATE_SEEK = 1
    STATE_RETURN = 2

    def __init__(self, player, orbit_index, total_roombas, collect_radius, speed_mult, range_mult=1.0):
        super().__init__()
        self.player = player
        self.collect_radius = collect_radius
        self.invincible = True  # Enemies ignore this sprite

        # Movement
        self.base_speed = 2.5 + (speed_mult * 20)  # Convert orbit_speed multiplier to linear speed
        self.speed = self.base_speed

        # Leash — how far roomba can stray from player before returning
        self.leash_radius = int(350 * range_mult)
        self.scan_radius = int(250 * range_mult)  # How far it can "see" gems

        # AI state
        self.state = self.STATE_WANDER
        self.target = None  # Target gem sprite or (x, y) wander point
        self.wander_timer = 0

        # Visual — neon roomba
        size = 20
        self.base_image = pygame.Surface((size, size), pygame.SRCALPHA)
        # Outer glow
        pygame.draw.circle(self.base_image, (0, 255, 255, 30), (size // 2, size // 2), size // 2)
        # Body
        pygame.draw.circle(self.base_image, (0, 200, 220), (size // 2, size // 2), size // 2 - 2)
        pygame.draw.circle(self.base_image, (0, 255, 255), (size // 2, size // 2), size // 2 - 2, 2)
        # Eye dot
        pygame.draw.circle(self.base_image, WHITE, (size // 2 + 3, size // 2 - 2), 3)
        pygame.draw.circle(self.base_image, (0, 50, 60), (size // 2 + 4, size // 2 - 2), 1)

        self.image = self.base_image.copy()
        self.rect = self.image.get_rect()

        # Start near the player with some offset

        angle = (orbit_index / max(1, total_roombas)) * (2 * math.pi)
        self.rect.centerx = player.rect.centerx + int(math.cos(angle) * 60)
        self.rect.centery = player.rect.centery + int(math.sin(angle) * 60)

        # Smooth float position
        self.fx = float(self.rect.centerx)
        self.fy = float(self.rect.centery)

        # Direction for sprite facing
        self.facing_x = 1

    def update(self):

        px, py = self.player.rect.center
        dist_to_player = math.hypot(self.fx - px, self.fy - py)

        # --- State transitions ---

        # Too far from player? Come back
        if dist_to_player > self.leash_radius and self.state != self.STATE_RETURN:
            self.state = self.STATE_RETURN
            self.target = None

        # Close enough after returning? Resume hunting
        if self.state == self.STATE_RETURN and dist_to_player < self.leash_radius * 0.6:
            self.state = self.STATE_WANDER
            self.wander_timer = 0

        # Wander timeout — pick a new wander point
        if self.state == self.STATE_WANDER:
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                # Random point near-ish to player
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(40, self.leash_radius * 0.7)
                self.target = (px + math.cos(angle) * dist, py + math.sin(angle) * dist)
                self.wander_timer = random.randint(60, 150)

        # --- Movement ---
        tx, ty = self.fx, self.fy  # Default: stay put

        if self.state == self.STATE_RETURN:
            tx, ty = px, py
            self.speed = self.base_speed * 1.5  # Hustle back
        elif self.state == self.STATE_SEEK and self.target is not None:
            # Target is a sprite — check if it's still alive
            if hasattr(self.target, 'alive') and not self.target.alive():
                self.state = self.STATE_WANDER
                self.target = None
                self.wander_timer = 0
            else:
                tx = self.target.rect.centerx if hasattr(self.target, 'rect') else self.target[0]
                ty = self.target.rect.centery if hasattr(self.target, 'rect') else self.target[1]
                self.speed = self.base_speed * 1.2
        elif self.state == self.STATE_WANDER and self.target is not None:
            tx, ty = self.target
            self.speed = self.base_speed * 0.8

        dx = tx - self.fx
        dy = ty - self.fy
        dist = math.hypot(dx, dy)

        if dist > 2:
            self.fx += (dx / dist) * self.speed
            self.fy += (dy / dist) * self.speed
            if dx != 0:
                self.facing_x = 1 if dx > 0 else -1

        self.rect.centerx = int(self.fx)
        self.rect.centery = int(self.fy)

        # Flip sprite based on direction
        if self.facing_x < 0:
            self.image = pygame.transform.flip(self.base_image, True, False)
        else:
            self.image = self.base_image.copy()

    def find_target(self, gem_group, gold_group=None):
        """Scan for the nearest gem or gold coin. Call each frame from the game loop."""
        if self.state == self.STATE_RETURN:
            return  # Don't get distracted while returning

        best_target = None
        best_dist = self.scan_radius

        # Check XP gems
        for gem in gem_group:
            dist = math.hypot(gem.rect.centerx - self.fx, gem.rect.centery - self.fy)
            if dist < best_dist:
                best_dist = dist
                best_target = gem

        # Check gold coins (slightly lower priority — only pick if closer)
        if gold_group:
            for coin in gold_group:
                dist = math.hypot(coin.rect.centerx - self.fx, coin.rect.centery - self.fy)
                if dist < best_dist * 0.8:  # Gold needs to be noticeably closer
                    best_dist = dist
                    best_target = coin

        if best_target is not None:
            self.state = self.STATE_SEEK
            self.target = best_target
        elif self.state == self.STATE_SEEK:
            # Lost target, go back to wandering
            self.state = self.STATE_WANDER
            self.wander_timer = 0

    def collect_gems(self, gem_group):
        """Return list of gems within pickup range."""
        collected = []
        for gem in gem_group:
            dist = math.hypot(gem.rect.centerx - self.rect.centerx,
                              gem.rect.centery - self.rect.centery)
            if dist <= self.collect_radius:
                collected.append(gem)
        return collected


class SpinningSaw(pygame.sprite.Sprite):
    """Orbital spinning saw that damages enemies on contact."""

    def __init__(self, player, orbit_index, total_saws, damage, orbit_speed, size_mult=1.0):
        super().__init__()
        self.player = player
        self.orbit_index = orbit_index
        self.total_saws = total_saws
        self.damage = damage
        self.orbit_speed = orbit_speed

        # Neon spinning saw blade
        size = max(16, int(28 * size_mult))
        self.base_image = pygame.Surface((size, size), pygame.SRCALPHA)
        # Outer glow
        pygame.draw.circle(self.base_image, (200, 200, 200, 25), (size // 2, size // 2), size // 2)
        # Blade body
        pygame.draw.circle(self.base_image, (180, 180, 200), (size // 2, size // 2), size // 2 - 3)
        pygame.draw.circle(self.base_image, (220, 220, 240), (size // 2, size // 2), size // 2 - 3, 2)
        # Teeth marks
        for t_angle in range(0, 360, 45):
            rad = math.radians(t_angle)
            tx = size // 2 + int((size // 2 - 1) * math.cos(rad))
            ty = size // 2 + int((size // 2 - 1) * math.sin(rad))
            pygame.draw.circle(self.base_image, (255, 255, 255), (tx, ty), 2)
        # Center
        pygame.draw.circle(self.base_image, (100, 100, 120), (size // 2, size // 2), 4)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect()

        # Orbital position
        self.orbit_distance = 60  # Distance from player
        self.angle = (orbit_index / total_saws) * (2 * math.pi)  # Evenly space saws
        self.rotation_angle = 0

        # Hit tracking (so same enemy isn't hit every frame)
        self.hit_cooldown = {}  # {enemy_id: frames_left}

    def update(self):
        # Orbit around player
        self.angle += self.orbit_speed
        offset_x = math.cos(self.angle) * self.orbit_distance
        offset_y = math.sin(self.angle) * self.orbit_distance
        self.rect.centerx = self.player.rect.centerx + offset_x
        self.rect.centery = self.player.rect.centery + offset_y

        # Spin the saw blade
        self.rotation_angle = (self.rotation_angle + 10) % 360
        self.image = pygame.transform.rotate(self.base_image, self.rotation_angle)
        self.rect = self.image.get_rect(center=self.rect.center)

        # Decrease hit cooldowns
        for enemy_id in list(self.hit_cooldown.keys()):
            self.hit_cooldown[enemy_id] -= 1
            if self.hit_cooldown[enemy_id] <= 0:
                del self.hit_cooldown[enemy_id]

    def can_hit_enemy(self, enemy):
        """Check if enough time has passed to hit this enemy again."""
        enemy_id = id(enemy)
        return enemy_id not in self.hit_cooldown

    def hit_enemy(self, enemy):
        """Mark enemy as hit, apply cooldown."""
        enemy_id = id(enemy)
        self.hit_cooldown[enemy_id] = 30  # 0.5 second cooldown at 60fps