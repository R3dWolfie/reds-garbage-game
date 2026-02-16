# settings_menu.py
"""Settings menu overlay — neon sliders, toggles, no unicode chars."""

import pygame, sys, math
from core.settings import *
from core.game_state import display_mgr, clock, menu_font, header_font, small_font, title_font


class SettingsMenu:
    def __init__(self, dm):
        self.dm = dm
        self.active = False
        current_res = tuple(self.dm.config["resolution"])
        self.res_index = RESOLUTIONS.index(current_res) if current_res in RESOLUTIONS else 2
        self.dragging = None
        self.slider_rects = []
        self.left_arrow = pygame.Rect(0,0,0,0)
        self.right_arrow = pygame.Rect(0,0,0,0)
        self.apply_btn = pygame.Rect(0,0,0,0)
        self.fs_btn = pygame.Rect(0,0,0,0)
        self.mouse_btn = pygame.Rect(0,0,0,0)
        self.back_btn = pygame.Rect(0,0,0,0)
        self.exit_btn = pygame.Rect(0,0,0,0)
        self._t = 0

    def open(self):
        self.active = True
        current_res = tuple(self.dm.config["resolution"])
        if current_res in RESOLUTIONS: self.res_index = RESOLUTIONS.index(current_res)

    def close(self): self.active = False; self.dragging = None

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
            gs2 = pygame.Surface((fw+4, th+4), pygame.SRCALPHA)
            gs2.fill((*color[:3], 20)); surf.blit(gs2, (x-2, ty-2))
        # Handle
        hx = x + fw - 6
        pygame.draw.rect(surf, (15,15,25), (hx, ty-3, 12, th+6), border_radius=3)
        pygame.draw.rect(surf, color, (hx, ty-3, 12, th+6), 2, border_radius=3)
        return tr, key

    def _toggle(self, surf, rect, label, on, color_on=(57,255,20), color_off=(255,60,60)):
        mx, my = pygame.mouse.get_pos()
        hov = rect.collidepoint(mx, my)
        c = color_on if on else color_off
        state = "ON" if on else "OFF"
        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((*c[:3], 30 if hov else 10))
        surf.blit(bg, rect.topleft)
        pygame.draw.rect(surf, c, rect, 2, border_radius=5)
        # Use small_font to ensure text fits
        txt_str = f"{label}: {state}"
        fnt = menu_font
        # Fall back to small font if text too wide
        if fnt.size(txt_str)[0] > rect.w - 12:
            fnt = small_font
        lt = fnt.render(txt_str, True, WHITE if hov else c)
        surf.blit(lt, (rect.centerx - lt.get_width()//2, rect.centery - lt.get_height()//2))
        return rect

    def _btn(self, surf, rect, text, color=(160,170,190)):
        mx, my = pygame.mouse.get_pos()
        hov = rect.collidepoint(mx, my)
        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((*color[:3], 35 if hov else 8))
        surf.blit(bg, rect.topleft)
        pygame.draw.rect(surf, color, rect, 2, border_radius=5)
        txt = menu_font.render(text, True, WHITE if hov else color)
        surf.blit(txt, (rect.centerx-txt.get_width()//2, rect.centery-txt.get_height()//2))
        return rect

    def run(self, background_surf):
        self.open()
        while self.active:
            self._t += 0.03
            sw = self.dm.config["resolution"][0]
            sh = self.dm.config["resolution"][1]
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
                    if self.apply_btn.collidepoint(mx, my):
                        self.dm.set_resolution(RESOLUTIONS[self.res_index])
                    if self.fs_btn.collidepoint(mx, my):
                        self.dm.toggle_fullscreen()
                    if self.mouse_btn.collidepoint(mx, my):
                        import core.settings as sm
                        sm.config["mouse_move"] = not sm.config.get("mouse_move", False)
                        sm.save_config(sm.config)
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
            # Fully opaque dark background — no particles bleed through
            surf.fill((5, 5, 15))

            # Panel
            pw, ph = min(500, sw-40), min(520, sh-40)
            px, py = sw//2-pw//2, sh//2-ph//2
            panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
            panel.fill((8,8,20,250))
            surf.blit(panel, (px, py))
            pygame.draw.rect(surf, (255,215,0), (px,py,pw,ph), 2, border_radius=8)

            tt = title_font.render("SETTINGS", True, (255,215,0))
            surf.blit(tt, (sw//2-tt.get_width()//2, py+14))

            cx, cy = px+25, py+58
            slider_w = pw-50

            # Resolution
            rl = small_font.render("RESOLUTION", True, (100,110,130))
            surf.blit(rl, (cx, cy)); cy += 22
            res_str = f"{RESOLUTIONS[self.res_index][0]} x {RESOLUTIONS[self.res_index][1]}"
            self.left_arrow = self._btn(surf, pygame.Rect(cx, cy, 40, 32), "<", (0,255,255))
            rt = menu_font.render(res_str, True, (0,255,255))
            surf.blit(rt, (cx+48, cy+4))
            self.right_arrow = self._btn(surf, pygame.Rect(cx+58+rt.get_width(), cy, 40, 32), ">", (0,255,255))
            self.apply_btn = self._btn(surf, pygame.Rect(cx+slider_w-100, cy, 100, 32), "Apply", (57,255,20))

            cy += 44
            # Toggles
            import core.settings as sm
            half_w = (slider_w - 10) // 2
            self.fs_btn = self._toggle(surf, pygame.Rect(cx, cy, half_w, 36),
                                        "Fullscreen", self.dm.config["fullscreen"])
            self.mouse_btn = self._toggle(surf, pygame.Rect(cx+half_w+10, cy, half_w, 36),
                                           "Mouse Move", sm.config.get("mouse_move", False),
                                           (0,200,255), (100,100,120))

            cy += 50
            # Sliders
            self.slider_rects = []
            colors = [(0,255,255), (57,255,20), (255,100,200)]
            labels = ["Master Volume", "SFX Volume", "Music Volume"]
            keys = ["master", "sfx", "music"]
            vals = [self.dm.config["master_volume"], self.dm.config["sfx_volume"], self.dm.config["music_volume"]]
            for i in range(3):
                t2, k = self._neon_slider(surf, cx, cy, slider_w, vals[i], labels[i], keys[i], colors[i])
                self.slider_rects.append((t2, k))
                cy += 55

            cy += 10
            half = (pw-50-10)//2
            self.back_btn = self._btn(surf, pygame.Rect(cx, cy, half, 38), "Back", (160,170,190))
            self.exit_btn = self._btn(surf, pygame.Rect(cx+half+10, cy, half, 38), "Quit Game", (255,30,60))

            pygame.display.flip()
            clock.tick(30)

settings_menu = SettingsMenu(display_mgr)