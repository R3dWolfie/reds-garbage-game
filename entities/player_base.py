# player_base.py
import pygame
import math
import core.settings as settings_module
from core.settings import *
from core.sprite_loader import load_sprite, make_neon_sprite


class PlayerBase(pygame.sprite.Sprite):
    """Base class for all player classes."""

    CLASS_KEY = "base"
    DISPLAY_NAME = "Base"
    SPRITE_FILE = "player_default.png"
    SPRITE_SIZE = (40, 40)
    SPRITE_COLOR = GREEN  # Fallback color
    NEON_GLOW_COLOR = (57, 255, 20)  # Default neon green

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
        "xp_gain": 1.0,
        "accuracy": 1.0,
    }

    def __init__(self):
        super().__init__()
        base_img = load_sprite(self.SPRITE_FILE, self.SPRITE_SIZE, self.SPRITE_COLOR, self.SPRITE_SIZE)
        self.image = make_neon_sprite(base_img, self.NEON_GLOW_COLOR, glow_size=5)
        self.original_image = self.image.copy()
        hurt_base = load_sprite(self.SPRITE_FILE, self.SPRITE_SIZE, RED, self.SPRITE_SIZE)
        self.hurt_image = make_neon_sprite(hurt_base, (255, 30, 60), glow_size=5)
        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        # Hat
        import core.settings as _sm
        self.equipped_hat = _sm.config.get("equipped_hat", None)

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
            "xp_gain": 0,
            "accuracy": 0,
        }

        # Leveling
        self.level = 1
        self.current_xp = 0
        self.xp_to_next_level = 8

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
        self._dash_target = None     # (x,y) for mouse-targeted dash, None for keyboard

    def reposition(self, sw, sh):
        self.rect.center = (sw // 2, sh // 2)

    def update(self):
        keys = pygame.key.get_pressed()
        speed = self.stats["speed"]
        import core.settings as _settings
        _dt = _settings.get_dt() if hasattr(_settings, 'get_dt') else 1.0

        # Track movement direction for dash
        move_dx, move_dy = 0, 0

        # Check if mouse movement is enabled
        use_mouse = _settings.config.get("mouse_move", False)


        if use_mouse:
            mx, my = pygame.mouse.get_pos()
            dx = mx - self.rect.centerx
            dy = my - self.rect.centery
            dist = math.hypot(dx, dy)
            deadzone = max(20, speed * 3)  # Don't jitter when close
            if dist > deadzone:
                move_dx = dx / dist
                move_dy = dy / dist
            else:
                move_dx, move_dy = 0, 0
        else:
            # Read keybinds from config
            _kb = _settings.config.get("keybinds", {})
            k_up = _kb.get("move_up", pygame.K_w)
            k_down = _kb.get("move_down", pygame.K_s)
            k_left = _kb.get("move_left", pygame.K_a)
            k_right = _kb.get("move_right", pygame.K_d)
            k_dash = _kb.get("dash", pygame.K_SPACE)

            if keys[k_up] or keys[pygame.K_UP]:    move_dy -= 1
            if keys[k_down] or keys[pygame.K_DOWN]:  move_dy += 1
            if keys[k_left] or keys[pygame.K_LEFT]:  move_dx -= 1
            if keys[k_right] or keys[pygame.K_RIGHT]: move_dx += 1

        # ---- DASH (hold key OR mouse1) ----
        _kb = _settings.config.get("keybinds", {})
        k_dash = _kb.get("dash", pygame.K_SPACE)
        mouse_buttons = pygame.mouse.get_pressed()
        dash_input = keys[k_dash] or mouse_buttons[0]
        if dash_input:
            if use_mouse or mouse_buttons[0]:
                mx, my = pygame.mouse.get_pos()
                self.try_dash(move_dx, move_dy, mouse_target=(mx, my))
            else:
                self.try_dash(move_dx, move_dy)

        if self.dash_duration > 0:
            # Currently dashing — apply burst movement, ignore normal input
            if self._dash_target is not None:
                # Mouse dash: stop at target
                tx, ty = self._dash_target
                dx_to = tx - self.rect.centerx
                dy_to = ty - self.rect.centery
                dist_to = math.hypot(dx_to, dy_to)
                step_dist = math.hypot(self.dash_dx, self.dash_dy)
                if dist_to <= step_dist + 2:
                    # Close enough — snap to target and end dash
                    self.rect.centerx = tx
                    self.rect.centery = ty
                    self.dash_duration = 0
                    self.dash_invincible = False
                else:
                    self.rect.x += self.dash_dx * _dt
                    self.rect.y += self.dash_dy * _dt
                    self.dash_duration -= _dt
                    self.dash_invincible = True
                    if self.dash_duration <= 0:
                        self.dash_duration = 0
                        self.dash_invincible = False
            else:
                self.rect.x += self.dash_dx * _dt
                self.rect.y += self.dash_dy * _dt
                self.dash_duration -= _dt
                self.dash_invincible = True
                if self.dash_duration <= 0:
                    self.dash_duration = 0
                    self.dash_invincible = False
        else:
            self.dash_invincible = False
            if use_mouse:
                self.rect.x += int(move_dx * speed * _dt)
                self.rect.y += int(move_dy * speed * _dt)
            else:
                self.rect.x += move_dx * speed * _dt
                self.rect.y += move_dy * speed * _dt

        # Cooldown tick (dt-aware)
        _dt = settings_module.get_dt() if hasattr(settings_module, 'get_dt') else 1.0
        if self.dash_cooldown > 0:
            self.dash_cooldown -= _dt

        sw = SCREEN_WIDTH
        sh = SCREEN_HEIGHT
        self.rect.clamp_ip(pygame.Rect(0, 0, sw, sh))

        # Reduce collision cooldown
        if self.collision_cooldown > 0:
            self.collision_cooldown -= _dt

    def try_dash(self, cur_dx=None, cur_dy=None, mouse_target=None):
        """Attempt a dash. Called each frame while space is held."""
        if self.dash_cooldown > 0 or self.dash_duration > 0:
            return False

        dx, dy = 0, 0
        if mouse_target is not None:
            # Dash toward mouse cursor
            tx, ty = mouse_target
            dx = tx - self.rect.centerx
            dy = ty - self.rect.centery
            dist_to_target = math.hypot(dx, dy)
            if dist_to_target < 10:
                return False  # Too close, don't dash
        elif cur_dx is not None and cur_dy is not None and (cur_dx != 0 or cur_dy != 0):
            dx, dy = cur_dx, cur_dy
        else:
            # Fallback to keyboard direction
            keys = pygame.key.get_pressed()
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
        self._dash_target = mouse_target  # None for keyboard, (x,y) for mouse
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
            self.stats["fire_rate"] = max(1, round(self.stats["fire_rate"] * 0.9, 1))
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
        elif upgrade_key == "xp_gain":
            self.stats["xp_gain"] = round(self.stats["xp_gain"] + 0.25, 2)
            self.upgrade_counts["xp_gain"] += 1
        elif upgrade_key == "accuracy":
            self.stats["accuracy"] = round(self.stats["accuracy"] + 0.2, 2)
            self.upgrade_counts["accuracy"] += 1

        # ---- Big ----
        elif upgrade_key == "big_speed":
            self.stats["speed"] += 3
            self.upgrade_counts["speed"] += 3
        elif upgrade_key == "big_fire_rate":
            self.stats["fire_rate"] = max(1, round(self.stats["fire_rate"] * 0.7, 1))
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
        elif upgrade_key == "big_xp_gain":
            self.stats["xp_gain"] = round(self.stats["xp_gain"] + 0.75, 2)
            self.upgrade_counts["xp_gain"] += 3
        elif upgrade_key == "big_accuracy":
            self.stats["accuracy"] = round(self.stats["accuracy"] + 0.6, 2)
            self.upgrade_counts["accuracy"] += 3

        # ---- Class-specific upgrades ----
        # Default (Survivor)
        elif upgrade_key == "balanced_boost":
            self.stats["damage"] += 1; self.stats["speed"] += 1
            self.stats["max_health"] += 10; self.current_health += 10
        elif upgrade_key == "survival_instinct":
            self.stats["max_health"] += 30; self.current_health += 30
            self.stats["speed"] += 1
        elif upgrade_key == "big_balanced":
            self.stats["damage"] += 3; self.stats["speed"] += 3
            self.stats["max_health"] += 20; self.current_health += 20

        # Tank
        elif upgrade_key == "ram_damage":
            self.stats["damage"] += 2  # Ram uses damage stat
        elif upgrade_key == "fortress":
            self.stats["max_health"] += 50; self.current_health += 50
            self.stats["damage"] += 1
            self.stats["speed"] = max(1, self.stats["speed"] - 1)
        elif upgrade_key == "big_ram":
            self.stats["damage"] += 4
            self.stats["max_health"] += 100; self.current_health += 100

        # Laser (Arcanist)
        elif upgrade_key == "beam_width":
            self.stats["bullet_size"] = round(self.stats["bullet_size"] + 0.4, 2)
        elif upgrade_key == "beam_bounce":
            self.stats["bullet_bounces"] = self.stats.get("bullet_bounces", 0) + 1
        elif upgrade_key == "big_beam":
            self.stats["bullet_size"] = round(self.stats["bullet_size"] + 1.0, 2)
            self.stats["bullet_bounces"] = self.stats.get("bullet_bounces", 0) + 2
            self.stats["damage"] += 3

        # Gunner
        elif upgrade_key == "bullet_storm":
            self.stats["multishot"] += 2
            self.stats["fire_rate"] = max(1, round(self.stats["fire_rate"] * 0.8, 1))
        elif upgrade_key == "explosive_rounds":
            self.stats["damage"] += 1
            self.stats["piercing"] += 2
        elif upgrade_key == "big_storm":
            self.stats["multishot"] += 4
            self.stats["fire_rate"] = max(1, round(self.stats["fire_rate"] * 0.6, 1))

        # Sniper
        elif upgrade_key == "headshot":
            if hasattr(self, 'crit_chance'):
                self.crit_chance = min(1.0, self.crit_chance + 0.30)
            self.stats["damage"] += 2
        elif upgrade_key == "long_range":
            self.stats["bullet_speed"] += 5
            self.stats["piercing"] += 2
        elif upgrade_key == "big_snipe":
            self.stats["damage"] += 5
            self.stats["piercing"] += 3

        # Paladin
        elif upgrade_key == "holy_aura":
            self.stats["damage"] += 1
        elif upgrade_key == "divine_shield":
            self.stats["max_health"] += 40; self.current_health += 40
        elif upgrade_key == "big_divine":
            self.stats["max_health"] += 80; self.current_health += 80
            self.stats["damage"] += 2

    def get_weapon_type(self):
        """Override in subclass. Returns 'bullet', 'laser', 'ram', etc."""
        return "bullet"

    def get_bullet_color(self):
        """Override in subclass for unique bullet visuals."""
        return (255, 255, 0)  # Default yellow

    def draw_magnet_ring(self, surf):
        """Draw the magnet radius as a neon ring."""
        radius = self.get_magnet_radius()
        if radius > 0:
            ring_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            # Outer glow
            pygame.draw.circle(ring_surf, (0, 255, 255, 15), (radius + 2, radius + 2), radius + 2)
            pygame.draw.circle(ring_surf, (0, 255, 255, 25), (radius + 2, radius + 2), radius, 2)
            # Inner bright ring
            pygame.draw.circle(ring_surf, (0, 200, 255, 50), (radius + 2, radius + 2), radius, 1)
            surf.blit(ring_surf, (self.rect.centerx - radius - 2, self.rect.centery - radius - 2))

    # ═══════════════════ HAT DRAWING ═══════════════════
    _hat_tick = 0  # Animation timer (class-level, shared)

    def draw_hat(self, surf):
        """Draw equipped hat on top of player sprite with animations."""
        if not self.equipped_hat:
            return
        from core.settings import HAT_DEFS
        hat_def = None
        for h in HAT_DEFS:
            if h["id"] == self.equipped_hat:
                hat_def = h; break
        if not hat_def or not hat_def.get("color"):
            return

        PlayerBase._hat_tick += 1
        t = PlayerBase._hat_tick
        cx = self.rect.centerx
        top = self.rect.top - 2
        c = hat_def["color"]
        hid = hat_def["id"]
        anim = hat_def.get("anim", None)

        # ── Draw base hat shape ──
        self._draw_hat_shape(surf, cx, top, c, hid, t)

        # ── Draw animation effects ──
        if anim:
            self._draw_hat_anim(surf, cx, top, c, anim, t)

    def _draw_hat_shape(self, surf, cx, top, c, hid, t):
        """Draw the static hat shape."""
        if hid == "beanie":
            pygame.draw.arc(surf, c, (cx-12, top-6, 24, 16), 0, math.pi, 4)
            pygame.draw.circle(surf, c, (cx, top-8), 3)
        elif hid == "cap":
            pygame.draw.rect(surf, c, (cx-14, top-3, 28, 6), border_radius=2)
            pygame.draw.rect(surf, c, (cx-10, top-9, 20, 8), border_radius=3)
            pygame.draw.line(surf, (min(255,c[0]+40),min(255,c[1]+40),min(255,c[2]+40)),
                             (cx-14, top-3), (cx-20, top), 2)
        elif hid == "headband":
            pygame.draw.rect(surf, c, (cx-14, top-2, 28, 4), border_radius=1)
        elif hid == "bandana":
            pts = [(cx-14, top-2), (cx+14, top-2), (cx+10, top+4), (cx-10, top+4)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.line(surf, c, (cx+10, top), (cx+18, top+6), 2)
        elif hid == "tophat":
            pygame.draw.rect(surf, c, (cx-16, top-2, 32, 5), border_radius=1)
            pygame.draw.rect(surf, c, (cx-10, top-18, 20, 18), border_radius=2)
            pygame.draw.rect(surf, (80,80,100), (cx-10, top-10, 20, 2))
        elif hid == "wizard":
            pts = [(cx, top-22), (cx-14, top), (cx+14, top)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.circle(surf, (255,255,100), (cx, top-22), 3)
            pygame.draw.line(surf, (120,80,220), (cx-8, top-6), (cx+8, top-6), 1)
        elif hid == "cowboy":
            pygame.draw.rect(surf, c, (cx-18, top-2, 36, 5), border_radius=1)
            pygame.draw.arc(surf, c, (cx-12, top-14, 24, 14), 0, math.pi, 3)
        elif hid == "beret":
            pygame.draw.ellipse(surf, c, (cx-14, top-10, 28, 14))
            pygame.draw.circle(surf, c, (cx+2, top-10), 3)
        elif hid == "antenna":
            pygame.draw.line(surf, c, (cx, top), (cx-6, top-18), 2)
            pygame.draw.line(surf, c, (cx, top), (cx+6, top-18), 2)
            a_pulse = int(abs(math.sin(t*0.15))*4)
            pygame.draw.circle(surf, c, (cx-6, top-18), 4+a_pulse)
            pygame.draw.circle(surf, c, (cx+6, top-18), 4+a_pulse)
        elif hid == "catears":
            pts_l = [(cx-12, top-2), (cx-14, top-14), (cx-4, top-2)]
            pts_r = [(cx+4, top-2), (cx+14, top-14), (cx+12, top-2)]
            pygame.draw.polygon(surf, c, pts_l)
            pygame.draw.polygon(surf, c, pts_r)
            ic = (min(255,c[0]+40), min(255,c[1]+20), min(255,c[2]+20))
            pygame.draw.polygon(surf, ic, [(cx-11, top-3), (cx-13, top-10), (cx-6, top-3)])
            pygame.draw.polygon(surf, ic, [(cx+6, top-3), (cx+13, top-10), (cx+11, top-3)])
        elif hid == "devilhorns":
            pygame.draw.line(surf, c, (cx-10, top), (cx-14, top-16), 3)
            pygame.draw.line(surf, c, (cx+10, top), (cx+14, top-16), 3)
            pygame.draw.circle(surf, (255,80,50), (cx-14, top-16), 2)
            pygame.draw.circle(surf, (255,80,50), (cx+14, top-16), 2)
        elif hid == "halo":
            fy = int(math.sin(t * 0.08) * 3)
            pygame.draw.ellipse(surf, (*c, 180), (cx-14, top-14+fy, 28, 8), 2)
            gs = pygame.Surface((36, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(gs, (*c, 40), (0, 0, 36, 16))
            surf.blit(gs, (cx-18, top-18+fy))
        elif hid == "crown":
            pts = [(cx-12, top), (cx-12, top-8), (cx-8, top-4), (cx-4, top-10),
                   (cx, top-4), (cx+4, top-10), (cx+8, top-4), (cx+12, top-8), (cx+12, top)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.polygon(surf, (200,170,0), pts, 2)
            pygame.draw.circle(surf, (255,50,50), (cx, top-6), 2)
        elif hid == "viking":
            pygame.draw.arc(surf, c, (cx-12, top-10, 24, 14), 0, math.pi, 3)
            pygame.draw.line(surf, c, (cx-12, top-4), (cx-18, top-16), 3)
            pygame.draw.line(surf, c, (cx+12, top-4), (cx+18, top-16), 3)
        elif hid == "hardhat":
            pygame.draw.arc(surf, c, (cx-14, top-8, 28, 18), 0, math.pi, 4)
            pygame.draw.rect(surf, c, (cx-16, top-1, 32, 4), border_radius=1)
        elif hid == "bucket":
            pygame.draw.rect(surf, c, (cx-12, top-10, 24, 14), border_radius=2)
            pygame.draw.rect(surf, (min(255,c[0]+30),min(255,c[1]+30),min(255,c[2]+30)),
                             (cx-14, top-1, 28, 3))
        elif hid == "party":
            pts = [(cx, top-18), (cx-10, top+2), (cx+10, top+2)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.circle(surf, (255,255,0), (cx, top-18), 3)
            pygame.draw.line(surf, (255,255,100), (cx-5, top-4), (cx+5, top-4), 1)
        elif hid == "bow":
            pygame.draw.polygon(surf, c, [(cx-12, top-2), (cx-4, top-6), (cx-4, top+2)])
            pygame.draw.polygon(surf, c, [(cx+12, top-2), (cx+4, top-6), (cx+4, top+2)])
            pygame.draw.circle(surf, (min(255,c[0]+40),min(255,c[1]+40),min(255,c[2]+40)), (cx, top-2), 3)
        elif hid == "earmuffs":
            pygame.draw.arc(surf, c, (cx-14, top-8, 28, 12), 0, math.pi, 2)
            pygame.draw.circle(surf, c, (cx-14, top-1), 5)
            pygame.draw.circle(surf, c, (cx+14, top-1), 5)
        elif hid == "fez":
            pygame.draw.rect(surf, c, (cx-8, top-10, 16, 14), border_radius=2)
            pygame.draw.rect(surf, c, (cx-10, top-1, 20, 3))
            pygame.draw.line(surf, (255,215,0), (cx, top-10), (cx+8, top-12), 2)
            pygame.draw.circle(surf, (255,215,0), (cx+8, top-12), 2)
        elif hid == "pirate":
            pygame.draw.arc(surf, c, (cx-14, top-8, 28, 14), 0, math.pi, 3)
            pygame.draw.rect(surf, c, (cx-16, top-2, 32, 4), border_radius=1)
            pygame.draw.circle(surf, (220,220,220), (cx, top-4), 4)
            pygame.draw.line(surf, (220,220,220), (cx-3, top), (cx+3, top), 1)
        elif hid == "chef":
            pygame.draw.circle(surf, c, (cx-6, top-10), 7)
            pygame.draw.circle(surf, c, (cx+6, top-10), 7)
            pygame.draw.circle(surf, c, (cx, top-12), 8)
            pygame.draw.rect(surf, c, (cx-10, top-4, 20, 6), border_radius=2)
        elif hid == "mohawk":
            for i in range(-6, 8, 3):
                h2 = 14 - abs(i)
                pygame.draw.line(surf, c, (cx+i, top), (cx+i, top-h2), 2)
        elif hid == "flower":
            colors = [(255,120,180),(255,200,100),(180,100,255),(100,200,255),(255,150,100)]
            for i, fc in enumerate(colors):
                angle = (i / 5) * math.pi * 2 - math.pi/2
                fx = cx + int(10 * math.cos(angle))
                fy = (top-4) + int(6 * math.sin(angle))
                pygame.draw.circle(surf, fc, (fx, fy), 4)
            pygame.draw.circle(surf, (255,255,100), (cx, top-4), 2)
        elif hid == "straw":
            pygame.draw.rect(surf, c, (cx-18, top-2, 36, 4), border_radius=1)
            pygame.draw.arc(surf, c, (cx-12, top-12, 24, 12), 0, math.pi, 3)
        elif hid == "bunnyears":
            bounce = int(abs(math.sin(t * 0.06)) * 3)
            pygame.draw.ellipse(surf, c, (cx-12, top-20-bounce, 8, 22))
            pygame.draw.ellipse(surf, c, (cx+4, top-20-bounce, 8, 22))
            pygame.draw.ellipse(surf, (255,180,190), (cx-10, top-16-bounce, 4, 14))
            pygame.draw.ellipse(surf, (255,180,190), (cx+6, top-16-bounce, 4, 14))
        elif hid == "propeller":
            pygame.draw.rect(surf, c, (cx-10, top-4, 20, 8), border_radius=3)
            angle = t * 0.3
            for a_off in [0, math.pi/2, math.pi, math.pi*1.5]:
                px = cx + int(10 * math.cos(angle + a_off))
                py = (top-6) + int(3 * math.sin(angle + a_off))
                pygame.draw.line(surf, (255,50,50), (cx, top-6), (px, py), 2)
            pygame.draw.circle(surf, (200,200,200), (cx, top-6), 2)
        elif hid == "shark":
            pts = [(cx, top-16), (cx-8, top+2), (cx+8, top+2)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.polygon(surf, (min(255,c[0]+30),min(255,c[1]+30),min(255,c[2]+30)), pts, 2)
        elif hid == "mushroom":
            pygame.draw.ellipse(surf, c, (cx-14, top-10, 28, 14))
            pygame.draw.rect(surf, (220,200,180), (cx-5, top-2, 10, 6), border_radius=2)
            pygame.draw.circle(surf, (255,255,255), (cx-6, top-6), 3)
            pygame.draw.circle(surf, (255,255,255), (cx+5, top-8), 2)
        elif hid == "samurai":
            pygame.draw.arc(surf, c, (cx-14, top-6, 28, 14), 0, math.pi, 3)
            pygame.draw.polygon(surf, (200,170,0), [(cx, top-14), (cx-4, top-4), (cx+4, top-4)])
            pygame.draw.line(surf, c, (cx-14, top), (cx-18, top+6), 2)
            pygame.draw.line(surf, c, (cx+14, top), (cx+18, top+6), 2)
        elif hid == "disco":
            pygame.draw.circle(surf, c, (cx, top-6), 8)
            for i in range(6):
                a = (i / 6) * math.pi * 2 + (t * 0.1)
                sx2 = cx + int(6 * math.cos(a))
                sy2 = (top-6) + int(6 * math.sin(a))
                sparkle_c = [(255,255,100),(100,255,255),(255,100,255)][i%3]
                pygame.draw.circle(surf, sparkle_c, (sx2, sy2), 2)
        elif hid == "flamehat":
            for i in range(-10, 12, 4):
                h2 = 10 + int(abs(math.sin(t*0.2+i*0.5))*8)
                a2 = max(100, 255 - h2*8)
                pygame.draw.line(surf, (255, max(50,200-h2*10), 0), (cx+i, top), (cx+i, top-h2), 3)
        elif hid == "icehat":
            pts = [(cx-10, top), (cx-6, top-12), (cx, top-6), (cx+6, top-12), (cx+10, top)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.polygon(surf, (200, 230, 255), pts, 2)
        elif hid == "voidhat":
            pygame.draw.ellipse(surf, c, (cx-14, top-6, 28, 10), 2)
            pygame.draw.circle(surf, (*c, 100), (cx, top-2), 8)
            pygame.draw.circle(surf, (40,0,60), (cx, top-2), 5)
        elif hid == "stormhat":
            pygame.draw.arc(surf, c, (cx-12, top-10, 24, 12), 0, math.pi, 3)
        elif hid == "hydrahat":
            for off in [-8, 0, 8]:
                pygame.draw.line(surf, c, (cx+off, top), (cx+off, top-12), 2)
                pygame.draw.circle(surf, c, (cx+off, top-12), 3)
                pygame.draw.circle(surf, (255,255,100), (cx+off, top-13), 1)
        elif hid == "phantomhat":
            vs = pygame.Surface((30, 18), pygame.SRCALPHA)
            a_v = int(40 + abs(math.sin(t*0.05))*30)
            vs.fill((*c, a_v))
            surf.blit(vs, (cx-15, top-14))
            pygame.draw.circle(surf, (*c, 150), (cx-5, top-6), 3)
            pygame.draw.circle(surf, (*c, 150), (cx+5, top-6), 3)
        elif hid == "fortresshat":
            pygame.draw.rect(surf, c, (cx-14, top-4, 28, 8))
            for bx in range(-12, 14, 6):
                pygame.draw.rect(surf, c, (cx+bx, top-10, 4, 6))
        elif hid == "neonhat":
            pygame.draw.rect(surf, (*c, 180), (cx-14, top-4, 28, 6), border_radius=3)
            gs2 = pygame.Surface((34, 12), pygame.SRCALPHA)
            pygame.draw.rect(gs2, (*c, 40), (0, 0, 34, 12), border_radius=5)
            surf.blit(gs2, (cx-17, top-7))
        elif hid == "omegahat":
            colors = [(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,200,255),(150,0,255)]
            fi = (t // 4) % len(colors)
            for i, rc in enumerate(colors):
                ci = (i + fi) % len(colors)
                pygame.draw.arc(surf, (*colors[ci], 180), (cx-14-i, top-14-i, 28+i*2, 10+i*2),
                                0, math.pi, 2)
        elif hid == "shadowhat":
            vs = pygame.Surface((32, 20), pygame.SRCALPHA)
            vs.fill((*c, 80))
            pygame.draw.rect(vs, (*c, 120), (0, 0, 32, 20), 2, border_radius=4)
            surf.blit(vs, (cx-16, top-12))
            # Eyes flicker
            ea = int(100 + abs(math.sin(t*0.1))*100)
            pygame.draw.circle(surf, (200,200,255,ea), (cx-5, top-4), 2)
            pygame.draw.circle(surf, (200,200,255,ea), (cx+5, top-4), 2)
        elif hid == "galaxyhat":
            pygame.draw.circle(surf, c, (cx, top-6), 10)
            for i in range(8):
                a = (i / 8) * math.pi * 2 + (t * 0.04)
                r2 = 6 + 3 * math.sin(a * 2 + t*0.05)
                sx2 = cx + int(r2 * math.cos(a))
                sy2 = (top-6) + int(r2 * math.sin(a))
                star_c = [(255,200,255),(200,150,255),(150,100,255),(255,255,200)][i%4]
                pygame.draw.circle(surf, star_c, (sx2, sy2), 1)
            pygame.draw.circle(surf, (255,255,200), (cx, top-6), 2)
        elif hid == "glitchhat":
            seed = (t // 3) % 10
            for i in range(5):
                gx = cx - 12 + ((i * 7 + seed) % 20)
                gy = top - 12 + ((i * 5 + seed) % 10)
                gw = 4 + (i % 3) * 3
                gc = [(255,0,255),(0,255,255),(255,255,0),(255,0,100),(0,255,100)][i]
                pygame.draw.rect(surf, (*gc, 160), (gx, gy, gw, 3))
        elif hid == "tinfoil":
            pts = [(cx-12, top), (cx-8, top-14), (cx+2, top-8), (cx+10, top-16), (cx+12, top)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.polygon(surf, (220,225,230), pts, 1)
        elif hid == "backwards_cap":
            pygame.draw.rect(surf, c, (cx-14, top-3, 28, 6), border_radius=2)
            pygame.draw.rect(surf, c, (cx-10, top-9, 20, 8), border_radius=3)
            pygame.draw.line(surf, (min(255,c[0]+40),min(255,c[1]+40),min(255,c[2]+40)),
                             (cx+14, top-3), (cx+20, top), 2)
        elif hid == "nightcap":
            pygame.draw.arc(surf, c, (cx-10, top-12, 20, 16), 0, math.pi, 3)
            pygame.draw.line(surf, c, (cx+10, top-6), (cx+16, top-14), 2)
            pygame.draw.circle(surf, (200,180,255), (cx+16, top-14), 3)
        elif hid == "afro":
            pygame.draw.circle(surf, c, (cx, top-8), 14)
            pygame.draw.circle(surf, (min(255,c[0]+20),min(255,c[1]+20),min(255,c[2]+20)), (cx-4, top-14), 4)
            pygame.draw.circle(surf, (min(255,c[0]+20),min(255,c[1]+20),min(255,c[2]+20)), (cx+6, top-12), 3)
        elif hid == "nurse":
            pygame.draw.rect(surf, c, (cx-10, top-6, 20, 10), border_radius=2)
            pygame.draw.line(surf, (255,50,50), (cx-3, top-4), (cx+3, top-4), 2)
            pygame.draw.line(surf, (255,50,50), (cx, top-7), (cx, top-1), 2)
        elif hid == "aviator":
            pygame.draw.circle(surf, c, (cx-8, top-1), 6, 2)
            pygame.draw.circle(surf, c, (cx+8, top-1), 6, 2)
            pygame.draw.line(surf, c, (cx-2, top-1), (cx+2, top-1), 2)
            # Lens tint
            ls = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(ls, (100,180,255,50), (5,5), 5)
            surf.blit(ls, (cx-13, top-6))
            surf.blit(ls, (cx+3, top-6))
        elif hid == "ushanka":
            pygame.draw.arc(surf, c, (cx-14, top-8, 28, 16), 0, math.pi, 4)
            # Ear flaps
            pygame.draw.rect(surf, (min(255,c[0]+30),min(255,c[1]+30),min(255,c[2]+30)),
                             (cx-16, top-2, 6, 10), border_radius=2)
            pygame.draw.rect(surf, (min(255,c[0]+30),min(255,c[1]+30),min(255,c[2]+30)),
                             (cx+10, top-2, 6, 10), border_radius=2)
        elif hid == "witchhat":
            pts = [(cx, top-24), (cx-14, top), (cx+14, top)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.rect(surf, c, (cx-16, top-2, 32, 4), border_radius=1)
            pygame.draw.circle(surf, (150,100,200), (cx+4, top-8), 2)
        elif hid == "antlers":
            # Left antler
            pygame.draw.line(surf, c, (cx-8, top), (cx-12, top-14), 2)
            pygame.draw.line(surf, c, (cx-12, top-14), (cx-16, top-10), 2)
            pygame.draw.line(surf, c, (cx-12, top-14), (cx-8, top-18), 2)
            # Right antler
            pygame.draw.line(surf, c, (cx+8, top), (cx+12, top-14), 2)
            pygame.draw.line(surf, c, (cx+12, top-14), (cx+16, top-10), 2)
            pygame.draw.line(surf, c, (cx+12, top-14), (cx+8, top-18), 2)
        elif hid == "tiara":
            pygame.draw.arc(surf, c, (cx-12, top-8, 24, 12), 0, math.pi, 2)
            pygame.draw.circle(surf, (255,200,255), (cx, top-8), 3)
            pygame.draw.circle(surf, (200,150,255), (cx-8, top-4), 2)
            pygame.draw.circle(surf, (200,150,255), (cx+8, top-4), 2)
        elif hid == "bloodcrown":
            pts = [(cx-12,top),(cx-12,top-8),(cx-8,top-4),(cx-4,top-10),
                   (cx,top-4),(cx+4,top-10),(cx+8,top-4),(cx+12,top-8),(cx+12,top)]
            pygame.draw.polygon(surf, c, pts)
        elif hid == "soulflame":
            for i in range(-8, 10, 4):
                h2 = 8 + int(abs(math.sin(t*0.15+i*0.7))*10)
                pygame.draw.line(surf, c, (cx+i, top), (cx+i, top-h2), 2)
        elif hid == "thunderhelm":
            pygame.draw.arc(surf, c, (cx-12, top-8, 24, 14), 0, math.pi, 3)
            pygame.draw.rect(surf, c, (cx-14, top-2, 28, 4))
        elif hid == "toxicmask":
            pygame.draw.ellipse(surf, c, (cx-12, top-8, 24, 12))
            pygame.draw.circle(surf, (0,0,0), (cx-5, top-4), 3)
            pygame.draw.circle(surf, (0,0,0), (cx+5, top-4), 3)
            pygame.draw.circle(surf, c, (cx-5, top-4), 1)
            pygame.draw.circle(surf, c, (cx+5, top-4), 1)
        elif hid == "magichat":
            pts = [(cx, top-22), (cx-14, top), (cx+14, top)]
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.circle(surf, (255,255,200), (cx, top-22), 3)
        elif hid == "phoenixhat":
            # Feathered plume
            for i, off in enumerate([-6, -3, 0, 3, 6]):
                h2 = 16 - abs(off)*2 + int(math.sin(t*0.12+i)*3)
                fc = (255, max(0, 120 - abs(off)*20), 0)
                pygame.draw.line(surf, fc, (cx+off, top), (cx+off, top-h2), 2)
        elif hid == "cosmichat":
            pygame.draw.circle(surf, c, (cx, top-6), 10)
            pygame.draw.circle(surf, (20,10,40), (cx, top-6), 7)
        else:
            # Fallback
            pygame.draw.circle(surf, c, (cx, top-6), 6, 2)

    def _draw_hat_anim(self, surf, cx, top, c, anim, t):
        """Draw animated effects for rare+ hats."""
        import random as _rnd

        if anim == "twitch":
            # Cat ears twitch occasionally
            if (t // 40) % 6 == 0:
                offset = int(math.sin(t * 0.8) * 2)
                pygame.draw.line(surf, (255,200,220), (cx-10, top-12+offset), (cx-10, top-8+offset), 2)

        elif anim == "pulse_glow":
            # Pulsing red glow
            pulse = abs(math.sin(t * 0.08))
            gs2 = pygame.Surface((40, 30), pygame.SRCALPHA)
            pygame.draw.circle(gs2, (*c, int(30 * pulse)), (20, 15), 18)
            surf.blit(gs2, (cx-20, top-20))

        elif anim == "float":
            pass  # Handled in shape (halo already floats)

        elif anim == "sparkle":
            # Random sparkles around hat
            for _ in range(2):
                sx = cx + _rnd.randint(-14, 14)
                sy = top + _rnd.randint(-14, 4)
                sa = _rnd.randint(80, 200)
                pygame.draw.circle(surf, (255,255,200,sa), (sx, sy), 1)

        elif anim == "bounce":
            pass  # Handled in shape

        elif anim == "spin":
            pass  # Handled in shape (propeller)

        elif anim == "spore":
            # Floating spore particles from mushroom
            for i in range(3):
                px = cx + int(math.sin(t*0.05 + i*2.1) * 12)
                py = top - 10 - (t + i * 17) % 20
                pa = max(0, 150 - ((t + i * 17) % 20) * 8)
                if pa > 0:
                    pygame.draw.circle(surf, (200,255,200,pa), (px, py), 2)

        elif anim == "rainbow_spin":
            # Rainbow light rays from disco ball
            for i in range(4):
                a = (i / 4) * math.pi * 2 + t * 0.15
                ex = cx + int(20 * math.cos(a))
                ey = (top-6) + int(12 * math.sin(a))
                rc = [(255,50,50),(50,255,50),(50,50,255),(255,255,50)][i]
                ls = pygame.Surface((abs(ex-cx)*2+4, abs(ey-top+6)*2+4), pygame.SRCALPHA)
                pygame.draw.line(surf, (*rc, 60), (cx, top-6), (ex, ey), 1)

        elif anim == "magic_dust":
            # Sparkling dust from witch hat
            for i in range(4):
                px = cx + int(math.sin(t*0.08 + i*1.5) * 16)
                py = top - 6 - (t*2 + i * 20) % 30
                pa = max(0, 180 - ((t*2 + i * 20) % 30) * 6)
                sc = [(200,150,255),(255,200,100),(150,100,255),(255,150,200)][i]
                if pa > 0:
                    pygame.draw.circle(surf, (*sc, pa), (px, py), _rnd.choice([1,1,2]))

        elif anim == "fire":
            # Animated fire on top
            for i in range(-10, 12, 3):
                h2 = 6 + int(abs(math.sin(t*0.25 + i*0.6)) * 12)
                fa = max(80, 255 - h2 * 12)
                fc = (255, max(50, 200 - h2*8), 0)
                pygame.draw.line(surf, fc, (cx+i, top-2), (cx+i+_rnd.randint(-2,2), top-2-h2), 2)
            # Ember particles
            for i in range(2):
                ex2 = cx + _rnd.randint(-8, 8)
                ey2 = top - 14 - (t + i*31) % 18
                ea = max(0, 200 - ((t + i*31) % 18) * 12)
                if ea > 0:
                    pygame.draw.circle(surf, (255, 180, 50, ea), (ex2, ey2), 1)

        elif anim == "frost":
            # Frost crystals + snowflakes
            for i in range(3):
                fx = cx + int(math.sin(t*0.04 + i*2.1) * 14)
                fy = top - 4 - (t + i * 23) % 24
                fa = max(0, 180 - ((t + i * 23) % 24) * 8)
                if fa > 0:
                    # Tiny snowflake cross
                    pygame.draw.line(surf, (200,230,255,fa), (fx-2, fy), (fx+2, fy), 1)
                    pygame.draw.line(surf, (200,230,255,fa), (fx, fy-2), (fx, fy+2), 1)
            # Icy glow
            gs3 = pygame.Surface((36, 20), pygame.SRCALPHA)
            ig = int(20 + abs(math.sin(t*0.06))*15)
            pygame.draw.ellipse(gs3, (150,220,255,ig), (0,0,36,20))
            surf.blit(gs3, (cx-18, top-14))

        elif anim == "void_swirl":
            # Dark particles spiraling inward
            for i in range(5):
                a = (i / 5) * math.pi * 2 + t * 0.06
                r2 = 14 - (t*0.3 + i*3) % 14
                vx = cx + int(r2 * math.cos(a))
                vy = (top-2) + int(r2 * 0.6 * math.sin(a))
                va = int(min(200, r2 * 15))
                if va > 20:
                    pygame.draw.circle(surf, (80,0,160,va), (vx, vy), max(1, int(r2*0.2)))

        elif anim == "lightning":
            # Random lightning bolts
            if (t % 20) < 4:
                for _ in range(2):
                    lx = cx + _rnd.randint(-10, 10)
                    ly = top - _rnd.randint(4, 16)
                    le = (lx + _rnd.randint(-8, 8), ly + _rnd.randint(6, 14))
                    mid = ((lx+le[0])//2 + _rnd.randint(-4,4), (ly+le[1])//2 + _rnd.randint(-4,4))
                    pygame.draw.line(surf, (255,255,200), (lx,ly), mid, 2)
                    pygame.draw.line(surf, (255,255,200), mid, le, 2)
                    pygame.draw.line(surf, (255,255,100), (lx,ly), mid, 1)
            # Ambient crackle
            if _rnd.random() < 0.3:
                sx3 = cx + _rnd.randint(-12, 12)
                sy3 = top + _rnd.randint(-14, 0)
                pygame.draw.circle(surf, (255,255,200,150), (sx3, sy3), 1)

        elif anim == "poison_drip":
            # Green drips falling
            for i in range(3):
                dx = cx - 6 + i * 6
                dy_off = (t*2 + i * 20) % 20
                da = max(0, 200 - dy_off * 10)
                if da > 0:
                    pygame.draw.circle(surf, (0,200,50,da), (dx, top + dy_off), 2)

        elif anim == "phase":
            # Phase in/out effect
            pa = int(40 + abs(math.sin(t*0.05)) * 40)
            ps = pygame.Surface((30, 18), pygame.SRCALPHA)
            ps.fill((180,150,255,pa))
            surf.blit(ps, (cx-15, top-14))

        elif anim == "shield_pulse":
            # Pulsing shield aura
            pr = int(16 + abs(math.sin(t*0.06)) * 6)
            gs4 = pygame.Surface((pr*2+4, pr*2+4), pygame.SRCALPHA)
            pa2 = int(20 + abs(math.sin(t*0.06)) * 20)
            pygame.draw.circle(gs4, (140,140,155,pa2), (pr+2,pr+2), pr, 2)
            surf.blit(gs4, (cx-pr-2, top-6-pr))

        elif anim == "neon_flicker":
            # Flickering neon glow
            flicker = 1.0 if _rnd.random() > 0.1 else 0.3
            gs5 = pygame.Surface((38, 16), pygame.SRCALPHA)
            pygame.draw.rect(gs5, (*c, int(50*flicker)), (0,0,38,16), border_radius=6)
            surf.blit(gs5, (cx-19, top-9))

        elif anim == "blood_drip":
            # Blood dripping from crown
            for i in range(4):
                dx2 = cx - 9 + i * 6
                dy2 = (t + i * 15) % 16
                da2 = max(0, 220 - dy2 * 14)
                if da2 > 0:
                    pygame.draw.circle(surf, (180,0,0,da2), (dx2, top + dy2), 2)
                    if dy2 < 4:
                        pygame.draw.line(surf, (180,0,0,da2), (dx2, top), (dx2, top+dy2), 1)

        elif anim == "soulfire":
            # Blue ethereal flames
            for i in range(-8, 10, 4):
                h2 = 6 + int(abs(math.sin(t*0.18 + i*0.8)) * 10)
                fc2 = (80, min(255, 180+h2*4), 255)
                pygame.draw.line(surf, fc2, (cx+i, top-2), (cx+i, top-2-h2), 2)
            # Soul wisps
            for i in range(2):
                wx = cx + int(math.sin(t*0.06+i*3)*16)
                wy = top - 10 - (t+i*25)%16
                wa = max(0, 160-((t+i*25)%16)*10)
                if wa > 0:
                    pygame.draw.circle(surf, (150,220,255,wa), (wx,wy), 2)

        elif anim == "toxic_bubble":
            # Toxic bubbles rising
            for i in range(3):
                bx = cx + int(math.sin(t*0.07+i*2)*10)
                by2 = top - 8 - (t+i*19)%22
                ba = max(0, 150-((t+i*19)%22)*7)
                br = 2 + ((t+i*19)%22)//8
                if ba > 0:
                    pygame.draw.circle(surf, (80,220,0,ba), (bx, by2), br, 1)

        elif anim == "magic_orbit":
            # Orbiting magic stars
            for i in range(3):
                a2 = (i / 3) * math.pi * 2 + t * 0.08
                orx = cx + int(14 * math.cos(a2))
                ory = (top-6) + int(8 * math.sin(a2))
                oc = [(255,200,100),(200,100,255),(100,200,255)][i]
                pygame.draw.circle(surf, oc, (orx, ory), 2)
                # Trail
                a3 = a2 - 0.3
                orx2 = cx + int(14 * math.cos(a3))
                ory2 = (top-6) + int(8 * math.sin(a3))
                pygame.draw.circle(surf, (*oc, 80), (orx2, ory2), 1)

        elif anim == "rainbow_halo":
            # Shifting rainbow ring
            colors = [(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,200,255),(150,0,255)]
            for i in range(16):
                a2 = (i / 16) * math.pi * 2 + t * 0.05
                rx = cx + int(16 * math.cos(a2))
                ry = (top-10) + int(6 * math.sin(a2))
                ci = (i + t // 4) % len(colors)
                pygame.draw.circle(surf, colors[ci], (rx, ry), 2)
            # Inner glow
            gs6 = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(gs6, (255,255,255,30), (10,10), 10)
            surf.blit(gs6, (cx-10, top-16))

        elif anim == "shadow_tendrils":
            # Dark tendrils reaching out
            for i in range(4):
                a2 = (i / 4) * math.pi * 2 + t * 0.03
                length = 10 + int(abs(math.sin(t*0.04+i))*10)
                ex3 = cx + int(length * math.cos(a2))
                ey3 = (top-4) + int(length * 0.5 * math.sin(a2))
                mid2 = (cx + int(length*0.5*math.cos(a2)) + _rnd.randint(-3,3),
                         (top-4) + int(length*0.3*math.sin(a2)) + _rnd.randint(-3,3))
                pygame.draw.line(surf, (40,40,60,120), (cx, top-4), mid2, 2)
                pygame.draw.line(surf, (40,40,60,80), mid2, (ex3, ey3), 1)

        elif anim == "galaxy_swirl":
            # Swirling stars
            for i in range(6):
                a2 = (i / 6) * math.pi * 2 + t * 0.05
                r3 = 8 + abs(math.sin(a2 + t*0.02)) * 6
                gx = cx + int(r3 * math.cos(a2))
                gy = (top-6) + int(r3 * math.sin(a2))
                gc2 = [(255,200,255),(200,150,255),(150,255,255),(255,255,150),(255,150,200),(150,200,255)][i]
                pygame.draw.circle(surf, gc2, (gx, gy), 1)
            # Nebula glow
            gs7 = pygame.Surface((28, 28), pygame.SRCALPHA)
            ng = int(15 + abs(math.sin(t*0.03))*15)
            pygame.draw.circle(gs7, (120,50,200,ng), (14,14), 14)
            surf.blit(gs7, (cx-14, top-20))

        elif anim == "glitch":
            # Glitch displacement
            if _rnd.random() < 0.15:
                gs8 = pygame.Surface((24, 6), pygame.SRCALPHA)
                gc3 = _rnd.choice([(255,0,255),(0,255,255),(255,255,0)])
                gs8.fill((*gc3, 100))
                surf.blit(gs8, (cx-12+_rnd.randint(-6,6), top-10+_rnd.randint(-8,4)))

        elif anim == "phoenix_fire":
            # Intense orange/gold flames + rising embers
            for i in range(-8, 10, 3):
                h2 = 8 + int(abs(math.sin(t*0.2+i*0.5))*14)
                fc3 = (255, max(80, 180-h2*5), 0)
                pygame.draw.line(surf, fc3, (cx+i, top-2), (cx+i, top-2-h2), 2)
            # Rising embers
            for i in range(4):
                ex4 = cx + int(math.sin(t*0.08+i*1.5)*14)
                ey4 = top - 16 - (t+i*17)%30
                ea2 = max(0, 220-((t+i*17)%30)*7)
                if ea2 > 0:
                    ec2 = (255, _rnd.randint(150,255), 0)
                    pygame.draw.circle(surf, (*ec2, ea2), (ex4, ey4), _rnd.choice([1,2]))

        elif anim == "cosmic_rings":
            # Multiple orbiting rings at different angles
            for ring in range(3):
                tilt = ring * 0.4 + 0.2
                for i in range(8):
                    a2 = (i / 8) * math.pi * 2 + t * (0.04 + ring*0.02)
                    rx2 = cx + int(14 * math.cos(a2))
                    ry2 = (top-8) + int(6 * tilt * math.sin(a2))
                    rc2 = [(255,150,255),(150,100,255),(100,200,255)][ring]
                    pygame.draw.circle(surf, (*rc2, 120), (rx2, ry2), 1)
            # Central star pulse
            sp = int(3 + abs(math.sin(t*0.1))*3)
            pygame.draw.circle(surf, (255,255,200), (cx, top-8), sp)
            # Glow
            gs9 = pygame.Surface((sp*4, sp*4), pygame.SRCALPHA)
            pygame.draw.circle(gs9, (200,180,255,30), (sp*2, sp*2), sp*2)
            surf.blit(gs9, (cx-sp*2, top-8-sp*2))