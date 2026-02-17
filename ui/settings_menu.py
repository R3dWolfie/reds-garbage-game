# settings_menu.py
"""Settings menu — tabbed categories, rebindable keys, no flicker."""

import pygame, sys, math
from core.settings import *
import core.settings as settings_module
from core.game_state import display_mgr, clock, menu_font, header_font, small_font, title_font, desc_font, gs
from ui.username_input import show_username_input

ACCENT = (0, 200, 255)
BG_DARK = (5, 6, 16)
TEXT_DIM = (60, 65, 80)
TEXT_MID = (130, 140, 160)
TEXT_BRIGHT = (220, 225, 240)
PANEL_BG = (10, 12, 24)
BORDER = (35, 40, 60)
TOGGLE_ON = (57, 255, 20)

WINDOW_MODES = ["Windowed", "Borderless", "Fullscreen"]

# Default keybinds
DEFAULT_KEYBINDS = {
    "move_up": pygame.K_w,
    "move_down": pygame.K_s,
    "move_left": pygame.K_a,
    "move_right": pygame.K_d,
    "dash": pygame.K_SPACE,
    "pause": pygame.K_ESCAPE,
    "auto_upgrade": pygame.K_q,
}

KEYBIND_LABELS = {
    "move_up": "Move Up",
    "move_down": "Move Down",
    "move_left": "Move Left",
    "move_right": "Move Right",
    "dash": "Dash",
    "pause": "Pause",
    "auto_upgrade": "Auto Upgrade",
}


def _key_name(keycode):
    """Human-readable key name."""
    name = pygame.key.name(keycode)
    return name.upper() if len(name) <= 3 else name.capitalize()


class SettingsMenu:
    def __init__(self, dm):
        self.dm = dm
        self.active = False
        self.res_index = 0
        self.fps_index = 1
        self.dragging = None
        self.slider_rects = []
        self.category = "display"
        self.rebinding = None  # Key action being rebound

    def _sync_indices(self):
        current_res = tuple(self.dm.config["resolution"])
        self.res_index = RESOLUTIONS.index(current_res) if current_res in RESOLUTIONS else 5
        fps = self.dm.config.get("fps", 60)
        self.fps_index = FPS_OPTIONS.index(fps) if fps in FPS_OPTIONS else 1

    def _get_window_mode(self):
        if self.dm.config.get("fullscreen", False): return 2
        if self.dm.config.get("borderless", False): return 1
        return 0

    def _set_window_mode(self, idx):
        self.dm.config["fullscreen"] = (idx == 2)
        self.dm.config["borderless"] = (idx == 1)
        self.dm.apply()

    def _get_keybinds(self):
        return settings_module.config.get("keybinds", DEFAULT_KEYBINDS.copy())

    def _set_keybind(self, action, keycode):
        if "keybinds" not in settings_module.config:
            settings_module.config["keybinds"] = DEFAULT_KEYBINDS.copy()
        settings_module.config["keybinds"][action] = keycode

    def open(self):
        self.active = True
        self._sync_indices()
        self.rebinding = None

    def close(self):
        self.active = False
        self.dragging = None
        self.rebinding = None
        settings_module.save_config(self.dm.config)

    # ── UI Components (no per-frame Surface allocation) ──

    def _back_btn(self, surf, mx, my):
        r = pygame.Rect(16, 16, 90, 34)
        hov = r.collidepoint(mx, my)
        c = ACCENT if hov else TEXT_DIM
        pygame.draw.rect(surf, c, r, 1 if not hov else 2, border_radius=5)
        t = small_font.render("< Back", True, TEXT_BRIGHT if hov else TEXT_MID)
        surf.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))
        return r

    def _btn(self, surf, rect, text, mx, my, active=False):
        hov = rect.collidepoint(mx, my)
        if active:
            pygame.draw.rect(surf, ACCENT, rect, 0, border_radius=5)
            # Darkened fill for semi-transparent look
            dark = pygame.Surface((rect.w - 4, rect.h - 4))
            dark.fill(PANEL_BG)
            dark.set_alpha(200)
            surf.blit(dark, (rect.x + 2, rect.y + 2))
            pygame.draw.rect(surf, ACCENT, rect, 2, border_radius=5)
            txt = menu_font.render(text, True, ACCENT)
        elif hov:
            pygame.draw.rect(surf, (25, 30, 50), rect, 0, border_radius=5)
            pygame.draw.rect(surf, ACCENT, rect, 1, border_radius=5)
            txt = menu_font.render(text, True, TEXT_BRIGHT)
        else:
            pygame.draw.rect(surf, (20, 22, 38), rect, 0, border_radius=5)
            pygame.draw.rect(surf, BORDER, rect, 1, border_radius=5)
            txt = menu_font.render(text, True, TEXT_MID)
        surf.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
        return hov

    def _toggle_btn(self, surf, rect, text, is_on, mx, my):
        hov = rect.collidepoint(mx, my)
        c = TOGGLE_ON if is_on else TEXT_DIM
        if hov:
            pygame.draw.rect(surf, (25, 30, 50), rect, 0, border_radius=5)
        else:
            pygame.draw.rect(surf, (15, 17, 30), rect, 0, border_radius=5)
        pygame.draw.rect(surf, c, rect, 1 if not hov else 2, border_radius=5)
        txt = small_font.render(text, True, c if not hov else TEXT_BRIGHT)
        surf.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
        return hov

    def _slider(self, surf, x, y, width, value, label, key, mx, my):
        lt = small_font.render(label, True, TEXT_MID)
        pct = int(value * 100)
        vt = small_font.render(f"{pct}%", True, ACCENT)
        surf.blit(lt, (x, y))
        surf.blit(vt, (x + width - vt.get_width(), y))
        ty = y + 22; th = 8
        tr = pygame.Rect(x, ty, width, th)
        pygame.draw.rect(surf, (20, 22, 38), tr, border_radius=4)
        fw = int(width * value)
        if fw > 0:
            pygame.draw.rect(surf, ACCENT, (x, ty, fw, th), border_radius=4)
        # Handle circle
        hx = x + fw
        pygame.draw.circle(surf, ACCENT, (hx, ty + th//2), 7)
        pygame.draw.circle(surf, PANEL_BG, (hx, ty + th//2), 4)
        return tr, key

    def _selector(self, surf, x, y, width, label, value_str, mx, my):
        lt = small_font.render(label, True, TEXT_DIM)
        surf.blit(lt, (x, y))
        y += 20
        # Left arrow
        left_r = pygame.Rect(x, y, 34, 30)
        lhov = left_r.collidepoint(mx, my)
        pygame.draw.rect(surf, (25, 30, 50) if lhov else (20, 22, 38), left_r, 0, border_radius=4)
        pygame.draw.rect(surf, ACCENT if lhov else BORDER, left_r, 1, border_radius=4)
        lt2 = menu_font.render("<", True, ACCENT if lhov else TEXT_MID)
        surf.blit(lt2, (left_r.centerx - lt2.get_width()//2, left_r.centery - lt2.get_height()//2))
        # Value
        vt = menu_font.render(value_str, True, TEXT_BRIGHT)
        surf.blit(vt, (x + 42 + (width - 120)//2 - vt.get_width()//2, y + 3))
        # Right arrow
        right_r = pygame.Rect(x + width - 34, y, 34, 30)
        rhov = right_r.collidepoint(mx, my)
        pygame.draw.rect(surf, (25, 30, 50) if rhov else (20, 22, 38), right_r, 0, border_radius=4)
        pygame.draw.rect(surf, ACCENT if rhov else BORDER, right_r, 1, border_radius=4)
        rt = menu_font.render(">", True, ACCENT if rhov else TEXT_MID)
        surf.blit(rt, (right_r.centerx - rt.get_width()//2, right_r.centery - rt.get_height()//2))
        return left_r, right_r

    # ── Main Loop ──

    def run(self, background_surf):
        self.open()

        back_r = apply_r = pygame.Rect(0, 0, 0, 0)
        res_left = res_right = fps_left = fps_right = pygame.Rect(0, 0, 0, 0)
        wm_left = wm_right = pygame.Rect(0, 0, 0, 0)
        vsync_r = mouse_r = username_r = pygame.Rect(0, 0, 0, 0)
        cat_rects = {}
        keybind_rects = {}  # {action: Rect}

        while self.active:
            sw = settings_module.SCREEN_WIDTH
            sh = settings_module.SCREEN_HEIGHT
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if event.type == pygame.KEYDOWN:
                    if self.rebinding:
                        # Rebinding mode: capture the key
                        if event.key != pygame.K_ESCAPE:
                            self._set_keybind(self.rebinding, event.key)
                        self.rebinding = None
                    elif event.key == pygame.K_ESCAPE:
                        self.close(); return

                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Sliders
                    for sr, sk in self.slider_rects:
                        if sr.inflate(0, 20).collidepoint(mx, my):
                            self.dragging = sk
                    # Category tabs
                    for cat, r in cat_rects.items():
                        if r.collidepoint(mx, my):
                            self.category = cat
                            self.rebinding = None
                    # Resolution
                    if res_left.collidepoint(mx, my):
                        self.res_index = (self.res_index - 1) % len(RESOLUTIONS)
                    if res_right.collidepoint(mx, my):
                        self.res_index = (self.res_index + 1) % len(RESOLUTIONS)
                    # FPS
                    if fps_left.collidepoint(mx, my):
                        self.fps_index = (self.fps_index - 1) % len(FPS_OPTIONS)
                        self.dm.set_fps(FPS_OPTIONS[self.fps_index])
                    if fps_right.collidepoint(mx, my):
                        self.fps_index = (self.fps_index + 1) % len(FPS_OPTIONS)
                        self.dm.set_fps(FPS_OPTIONS[self.fps_index])
                    # Window mode
                    if wm_left.collidepoint(mx, my):
                        self._set_window_mode((self._get_window_mode() - 1) % 3)
                    if wm_right.collidepoint(mx, my):
                        self._set_window_mode((self._get_window_mode() + 1) % 3)
                    # Apply resolution
                    if apply_r.collidepoint(mx, my):
                        self.dm.set_resolution(RESOLUTIONS[self.res_index])
                        settings_module.save_config(self.dm.config)
                    # VSync
                    if vsync_r.collidepoint(mx, my):
                        self.dm.set_vsync(not self.dm.config.get("vsync", False))
                    # Mouse
                    if mouse_r.collidepoint(mx, my):
                        settings_module.config["mouse_move"] = not settings_module.config.get("mouse_move", False)
                    # Username
                    if username_r.collidepoint(mx, my):
                        show_username_input()
                    # Keybind rebinding or reset
                    for action, r in keybind_rects.items():
                        if r.collidepoint(mx, my):
                            if action == "__reset__":
                                settings_module.config["keybinds"] = DEFAULT_KEYBINDS.copy()
                                self.rebinding = None
                            else:
                                self.rebinding = action
                    # Back
                    if back_r.collidepoint(mx, my):
                        self.close(); return

                if event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = None

            # Drag sliders
            if self.dragging:
                for sr, sk in self.slider_rects:
                    if sk == self.dragging:
                        val = max(0.0, min(1.0, (mx - sr.x) / sr.width))
                        if sk == "master": self.dm.set_master_volume(val)
                        elif sk == "sfx": self.dm.set_sfx_volume(val)
                        elif sk == "music": self.dm.set_music_volume(val)

            # ── DRAW ──
            surf = self.dm.get_screen()
            surf.fill(BG_DARK)

            # Panel
            pw, ph = 560, 520
            px, py = sw//2 - pw//2, sh//2 - ph//2
            pygame.draw.rect(surf, PANEL_BG, (px, py, pw, ph), 0, border_radius=10)
            pygame.draw.rect(surf, BORDER, (px, py, pw, ph), 1, border_radius=10)

            # Title
            tt = menu_font.render("SETTINGS", True, TEXT_BRIGHT)
            surf.blit(tt, (sw//2 - tt.get_width()//2, py + 16))

            # Back button (top-left)
            back_r = self._back_btn(surf, mx, my)

            # Category tabs
            tab_y = py + 48
            categories = ["general", "display", "audio", "controls"]
            cat_labels = ["General", "Display", "Audio", "Controls"]
            tab_w = (pw - 50) // 4 - 6
            cat_rects = {}
            for i, (cat, lbl) in enumerate(zip(categories, cat_labels)):
                r = pygame.Rect(px + 25 + i * (tab_w + 8), tab_y, tab_w, 32)
                cat_rects[cat] = r
                self._btn(surf, r, lbl, mx, my, active=(self.category == cat))

            # Content area
            cx, cy = px + 30, tab_y + 50
            content_w = pw - 60
            self.slider_rects = []
            keybind_rects = {}

            # Reset all interaction rects to avoid stale clicks
            res_left = res_right = fps_left = fps_right = pygame.Rect(0, 0, 0, 0)
            wm_left = wm_right = pygame.Rect(0, 0, 0, 0)
            vsync_r = mouse_r = username_r = apply_r = pygame.Rect(0, 0, 0, 0)

            if self.category == "general":
                # Username
                uname = gs.local_username
                lbl = small_font.render("USERNAME", True, TEXT_DIM)
                surf.blit(lbl, (cx, cy)); cy += 22
                username_r = pygame.Rect(cx, cy, content_w, 38)
                hov = username_r.collidepoint(mx, my)
                pygame.draw.rect(surf, (25, 30, 50) if hov else (18, 20, 35), username_r, 0, border_radius=5)
                pygame.draw.rect(surf, ACCENT if hov else BORDER, username_r, 1 if not hov else 2, border_radius=5)
                uv = menu_font.render(uname, True, ACCENT)
                surf.blit(uv, (cx + 14, cy + 8))
                hint = desc_font.render("Click to change", True, TEXT_DIM)
                surf.blit(hint, (cx + content_w - hint.get_width() - 14, cy + 12))

            elif self.category == "display":
                # Resolution selector
                res_str = f"{RESOLUTIONS[self.res_index][0]} x {RESOLUTIONS[self.res_index][1]}"
                res_left, res_right = self._selector(surf, cx, cy, content_w - 100, "RESOLUTION", res_str, mx, my)
                apply_r = pygame.Rect(cx + content_w - 80, cy + 18, 80, 32)
                self._btn(surf, apply_r, "Apply", mx, my)
                cy += 60

                # FPS selector
                fps_label = FPS_LABELS[self.fps_index]
                fps_left, fps_right = self._selector(surf, cx, cy, content_w//2, "FPS LIMIT", fps_label, mx, my)
                actual_fps = int(clock.get_fps())
                fps_txt = small_font.render(f"Current: {actual_fps} fps", True, TEXT_DIM)
                surf.blit(fps_txt, (cx + content_w//2 + 30, cy + 22))
                cy += 60

                # Window mode (3-way)
                wm_idx = self._get_window_mode()
                wm_left, wm_right = self._selector(surf, cx, cy, content_w, "WINDOW MODE", WINDOW_MODES[wm_idx], mx, my)
                cy += 60

                # VSync toggle
                vs_on = self.dm.config.get("vsync", False)
                vsync_r = pygame.Rect(cx, cy, content_w//2 - 8, 36)
                self._toggle_btn(surf, vsync_r, f"VSync: {'On' if vs_on else 'Off'}", vs_on, mx, my)

                # Mouse toggle
                mo_on = settings_module.config.get("mouse_move", False)
                mouse_r = pygame.Rect(cx + content_w//2 + 8, cy, content_w//2 - 8, 36)
                self._toggle_btn(surf, mouse_r, f"Mouse Aim: {'On' if mo_on else 'Off'}", mo_on, mx, my)

            elif self.category == "audio":
                labels = ["Master Volume", "SFX Volume", "Music Volume"]
                keys = ["master", "sfx", "music"]
                vals = [self.dm.config["master_volume"], self.dm.config["sfx_volume"], self.dm.config["music_volume"]]
                for i in range(3):
                    sr, sk = self._slider(surf, cx, cy, content_w, vals[i], labels[i], keys[i], mx, my)
                    self.slider_rects.append((sr, sk))
                    cy += 54

            elif self.category == "controls":
                # Keybinds header
                sep = small_font.render("KEYBINDS", True, TEXT_DIM)
                surf.blit(sep, (cx, cy))
                cy += 24

                # Rebind hint
                if self.rebinding:
                    hint = desc_font.render(f"Press a key for '{KEYBIND_LABELS.get(self.rebinding, self.rebinding)}'...", True, (255, 200, 50))
                    surf.blit(hint, (cx, cy))
                    cy += 22

                binds = self._get_keybinds()
                for action, label in KEYBIND_LABELS.items():
                    keycode = binds.get(action, DEFAULT_KEYBINDS.get(action, 0))
                    row_r = pygame.Rect(cx, cy, content_w, 28)
                    keybind_rects[action] = row_r
                    hov = row_r.collidepoint(mx, my)
                    is_rebinding = (self.rebinding == action)

                    if is_rebinding:
                        pygame.draw.rect(surf, (40, 35, 15), row_r, 0, border_radius=4)
                        pygame.draw.rect(surf, (255, 200, 50), row_r, 1, border_radius=4)
                    elif hov:
                        pygame.draw.rect(surf, (22, 25, 42), row_r, 0, border_radius=4)

                    at = small_font.render(label, True, TEXT_BRIGHT if hov or is_rebinding else TEXT_MID)
                    if is_rebinding:
                        kt = small_font.render("...", True, (255, 200, 50))
                    else:
                        kt = small_font.render(_key_name(keycode), True, ACCENT)
                    surf.blit(at, (cx + 12, cy + 5))
                    surf.blit(kt, (cx + content_w - kt.get_width() - 12, cy + 5))
                    cy += 32

                # Reset keybinds button
                reset_r = pygame.Rect(cx, cy + 8, 160, 30)
                rhov = reset_r.collidepoint(mx, my)
                pygame.draw.rect(surf, (25, 30, 50) if rhov else (18, 20, 35), reset_r, 0, border_radius=5)
                pygame.draw.rect(surf, (255, 80, 80) if rhov else BORDER, reset_r, 1, border_radius=5)
                rt = small_font.render("Reset Defaults", True, (255, 80, 80) if rhov else TEXT_DIM)
                surf.blit(rt, (reset_r.centerx - rt.get_width()//2, reset_r.centery - rt.get_height()//2))
                keybind_rects["__reset__"] = reset_r

            display_mgr.present()
            clock.tick(settings_module.FPS or 0)


settings_menu = SettingsMenu(display_mgr)