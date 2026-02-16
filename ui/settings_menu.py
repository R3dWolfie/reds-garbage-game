# settings_menu.py
"""Settings menu overlay — neon sliders, toggles, FPS, vsync, borderless."""

import pygame, sys, math
from core.settings import *
import core.settings as settings_module
from core.game_state import display_mgr, clock, menu_font, header_font, small_font, title_font


class SettingsMenu:
    def __init__(self, dm):
        self.dm = dm
        self.active = False
        current_res = tuple(self.dm.config["resolution"])
        self.res_index = RESOLUTIONS.index(current_res) if current_res in RESOLUTIONS else 5
        self.fps_index = self._get_fps_index()
        self.dragging = None
        self.slider_rects = []
        self.left_arrow = pygame.Rect(0,0,0,0)
        self.right_arrow = pygame.Rect(0,0,0,0)
        self.fps_left = pygame.Rect(0,0,0,0)
        self.fps_right = pygame.Rect(0,0,0,0)
        self.apply_btn = pygame.Rect(0,0,0,0)
        self.fs_btn = pygame.Rect(0,0,0,0)
        self.borderless_btn = pygame.Rect(0,0,0,0)
        self.vsync_btn = pygame.Rect(0,0,0,0)
        self.mouse_btn = pygame.Rect(0,0,0,0)
        self.back_btn = pygame.Rect(0,0,0,0)
        self.exit_btn = pygame.Rect(0,0,0,0)
        self._t = 0

    def _get_fps_index(self):
        fps = self.dm.config.get("fps", 60)
        if fps in FPS_OPTIONS:
            return FPS_OPTIONS.index(fps)
        return 1  # default to 60

    def open(self):
        self.active = True
        current_res = tuple(self.dm.config["resolution"])
        if current_res in RESOLUTIONS: self.res_index = RESOLUTIONS.index(current_res)
        self.fps_index = self._get_fps_index()

    def close(self):
        self.active = False
        self.dragging = None
        settings_module.save_config(self.dm.config)

    def _neon_slider(self, surf, x, y, width, value, label, key, color=(0,255,255)):
        pct = int(value * 100)
        lt = menu_font.render(label, True, (170,180,195))
        vt = menu_font.render(f"{pct}%", True, color)
        surf.blit(lt, (x, y)); surf.blit(vt, (x+width-vt.get_width(), y))
        ty = y + 26; th = 8
        tr = pygame.Rect(x, ty, width, th)
        pygame.draw.rect(surf, (20,20,35), tr, border_radius=4)
        fw = int(width * value)
        if fw > 0:
            pygame.draw.rect(surf, color, (x, ty, fw, th), border_radius=4)
            gs2 = pygame.Surface((fw+4, th+4))
            gs2.fill(color[:3])
            gs2.set_alpha(20); surf.blit(gs2, (x-2, ty-2))
        hx = x + fw - 6
        pygame.draw.rect(surf, (15,15,25), (hx, ty-3, 12, th+6), border_radius=3)
        pygame.draw.rect(surf, color, (hx, ty-3, 12, th+6), 2, border_radius=3)
        return tr, key

    def _toggle(self, surf, rect, label, on, color_on=(57,255,20), color_off=(255,60,60)):
        mx, my = pygame.mouse.get_pos()
        hov = rect.collidepoint(mx, my)
        c = color_on if on else color_off
        state = "ON" if on else "OFF"
        bg = pygame.Surface((rect.w, rect.h))
        bg.fill(c[:3])
        bg.set_alpha(30 if hov else 10)
        surf.blit(bg, rect.topleft)
        pygame.draw.rect(surf, c, rect, 2, border_radius=5)
        txt_str = f"{label}: {state}"
        fnt = menu_font
        if fnt.size(txt_str)[0] > rect.w - 12:
            fnt = small_font
        lt = fnt.render(txt_str, True, WHITE if hov else c)
        surf.blit(lt, (rect.centerx - lt.get_width()//2, rect.centery - lt.get_height()//2))
        return rect

    def _btn(self, surf, rect, text, color=(160,170,190)):
        mx, my = pygame.mouse.get_pos()
        hov = rect.collidepoint(mx, my)
        bg = pygame.Surface((rect.w, rect.h))
        bg.fill(color[:3])
        bg.set_alpha(35 if hov else 8)
        surf.blit(bg, rect.topleft)
        pygame.draw.rect(surf, color, rect, 2, border_radius=5)
        txt = menu_font.render(text, True, WHITE if hov else color)
        surf.blit(txt, (rect.centerx-txt.get_width()//2, rect.centery-txt.get_height()//2))
        return rect

    def _selector(self, surf, x, y, width, label, value_str, color=(0,255,255)):
        """Draw a left/right selector widget. Returns (left_rect, right_rect)."""
        lt = small_font.render(label, True, (100,110,130))
        surf.blit(lt, (x, y))
        y += 20
        left_r = self._btn(surf, pygame.Rect(x, y, 36, 30), "<", color)
        vt = menu_font.render(value_str, True, color)
        surf.blit(vt, (x + 44 + (width-120)//2 - vt.get_width()//2, y + 3))
        right_r = self._btn(surf, pygame.Rect(x + width - 36, y, 36, 30), ">", color)
        return left_r, right_r

    def run(self, background_surf):
        self.open()
        while self.active:
            self._t += 0.03
            sw = settings_module.SCREEN_WIDTH
            sh = settings_module.SCREEN_HEIGHT
            mx, my = pygame.mouse.get_pos()
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: self.close(); return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for sr, sk in self.slider_rects:
                        if sr.inflate(0, 20).collidepoint(mx, my): self.dragging = sk
                    if self.left_arrow.collidepoint(mx, my):
                        self.res_index = (self.res_index - 1) % len(RESOLUTIONS)
                    if self.right_arrow.collidepoint(mx, my):
                        self.res_index = (self.res_index + 1) % len(RESOLUTIONS)
                    if self.fps_left.collidepoint(mx, my):
                        self.fps_index = (self.fps_index - 1) % len(FPS_OPTIONS)
                        self.dm.set_fps(FPS_OPTIONS[self.fps_index])
                    if self.fps_right.collidepoint(mx, my):
                        self.fps_index = (self.fps_index + 1) % len(FPS_OPTIONS)
                        self.dm.set_fps(FPS_OPTIONS[self.fps_index])
                    if self.apply_btn.collidepoint(mx, my):
                        self.dm.set_resolution(RESOLUTIONS[self.res_index])
                    if self.fs_btn.collidepoint(mx, my):
                        self.dm.toggle_fullscreen()
                    if self.borderless_btn.collidepoint(mx, my):
                        self.dm.set_borderless(not self.dm.config.get("borderless", True))
                    if self.vsync_btn.collidepoint(mx, my):
                        self.dm.set_vsync(not self.dm.config.get("vsync", False))
                    if self.mouse_btn.collidepoint(mx, my):
                        settings_module.config["mouse_move"] = not settings_module.config.get("mouse_move", False)
                        settings_module.save_config(settings_module.config)
                    if self.back_btn.collidepoint(mx, my): self.close(); return
                    if self.exit_btn.collidepoint(mx, my): pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONUP: self.dragging = None

            if self.dragging:
                for sr, sk in self.slider_rects:
                    if sk == self.dragging:
                        val = max(0.0, min(1.0, (mx - sr.x) / sr.width))
                        if sk == "master": self.dm.set_master_volume(val)
                        elif sk == "sfx": self.dm.set_sfx_volume(val)
                        elif sk == "music": self.dm.set_music_volume(val)

            surf = self.dm.get_screen()
            surf.fill((5, 5, 15))

            # Panel
            pw, ph = 520, 640
            px, py = sw//2-pw//2, sh//2-ph//2
            panel = pygame.Surface((pw, ph))
            panel.fill((8,8,20))
            panel.set_alpha(250)
            surf.blit(panel, (px, py))
            pygame.draw.rect(surf, (255,215,0), (px,py,pw,ph), 2, border_radius=8)

            tt = title_font.render("SETTINGS", True, (255,215,0))
            surf.blit(tt, (sw//2-tt.get_width()//2, py+10))

            cx, cy = px+25, py+52
            slider_w = pw-50

            # ── DISPLAY ──
            section = header_font.render("DISPLAY", True, (0,200,255))
            surf.blit(section, (cx, cy)); cy += 26

            # Resolution selector
            res_str = f"{RESOLUTIONS[self.res_index][0]} x {RESOLUTIONS[self.res_index][1]}"
            self.left_arrow, self.right_arrow = self._selector(
                surf, cx, cy, slider_w, "RESOLUTION", res_str, (0,255,255))
            self.apply_btn = self._btn(surf, pygame.Rect(cx+slider_w-90, cy, 90, 30), "Apply", (57,255,20))
            cy += 56

            # FPS selector
            fps_label = FPS_LABELS[self.fps_index]
            self.fps_left, self.fps_right = self._selector(
                surf, cx, cy, slider_w//2, "FPS LIMIT", fps_label, (255,200,50))
            # Current FPS counter
            actual_fps = int(clock.get_fps())
            fps_txt = small_font.render(f"Current: {actual_fps} fps", True, (120,130,140))
            surf.blit(fps_txt, (cx + slider_w//2 + 20, cy + 22))
            cy += 56

            # Toggles row: Fullscreen, Borderless, Vsync
            tw = (slider_w - 16) // 3
            self.fs_btn = self._toggle(surf, pygame.Rect(cx, cy, tw, 34),
                                        "Fullscreen", self.dm.config.get("fullscreen", True))
            self.borderless_btn = self._toggle(surf, pygame.Rect(cx+tw+8, cy, tw, 34),
                                                "Borderless", self.dm.config.get("borderless", True),
                                                (0,200,255), (100,100,120))
            self.vsync_btn = self._toggle(surf, pygame.Rect(cx+tw*2+16, cy, tw, 34),
                                           "VSync", self.dm.config.get("vsync", False),
                                           (255,200,50), (100,100,120))
            cy += 46

            # Mouse move toggle
            self.mouse_btn = self._toggle(surf, pygame.Rect(cx, cy, slider_w, 34),
                                           "Mouse Aim/Move", settings_module.config.get("mouse_move", False),
                                           (0,200,255), (100,100,120))
            cy += 50

            # ── AUDIO ──
            section2 = header_font.render("AUDIO", True, (255,100,200))
            surf.blit(section2, (cx, cy)); cy += 26

            self.slider_rects = []
            colors = [(0,255,255), (57,255,20), (255,100,200)]
            labels = ["Master Volume", "SFX Volume", "Music Volume"]
            keys = ["master", "sfx", "music"]
            vals = [self.dm.config["master_volume"], self.dm.config["sfx_volume"], self.dm.config["music_volume"]]
            for i in range(3):
                t2, k = self._neon_slider(surf, cx, cy, slider_w, vals[i], labels[i], keys[i], colors[i])
                self.slider_rects.append((t2, k))
                cy += 48

            cy += 8
            half = (pw-50-10)//2
            self.back_btn = self._btn(surf, pygame.Rect(cx, cy, half, 38), "Back", (160,170,190))
            self.exit_btn = self._btn(surf, pygame.Rect(cx+half+10, cy, half, 38), "Quit Game", (255,30,60))

            display_mgr.present()
            clock.tick(settings_module.FPS or 0)


settings_menu = SettingsMenu(display_mgr)