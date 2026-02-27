# username_input.py
"""Username entry screen — matches global UI standards."""

import pygame
import sys
import core.settings as settings_module
from core.settings import *
from core.game_state import (
    display_mgr, clock, gs,
    header_font, title_font, menu_font, small_font, desc_font
)

ACCENT = (0, 200, 255)
BG_DARK = (5, 6, 16)
PANEL_BG = (10, 12, 24)
TEXT_DIM = (60, 65, 80)
TEXT_MID = (130, 140, 160)
TEXT_BRIGHT = (220, 225, 240)
BORDER = (35, 40, 60)


def _save_username(name):
    settings_module.config["username"] = name
    settings_module.save_config(settings_module.config)


def show_username_input():
    """Ask the player to enter a username."""
    username = gs.local_username
    MAX_LEN = 16
    _t = 0.0

    while True:
        _t += 0.03
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)

        # Panel
        pw, ph = 440, 240
        px, py = sw//2 - pw//2, sh//2 - ph//2
        pygame.draw.rect(surf, PANEL_BG, (px, py, pw, ph), 0, border_radius=10)
        pygame.draw.rect(surf, BORDER, (px, py, pw, ph), 1, border_radius=10)

        # Title
        tt = title_font.render("ENTER USERNAME", True, TEXT_BRIGHT)
        surf.blit(tt, (sw//2 - tt.get_width()//2, py + 18))

        # Hint
        ht = desc_font.render("Your name appears above your character in game", True, TEXT_DIM)
        surf.blit(ht, (sw//2 - ht.get_width()//2, py + 52))

        # Input box
        box_w, box_h = pw - 50, 42
        box_x = px + 25
        box_y = py + 80
        box_r = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(surf, (18, 22, 40), box_r, 0, border_radius=6)
        pygame.draw.rect(surf, ACCENT, box_r, 2, border_radius=6)

        cursor = "|" if int(_t * 4) % 2 == 0 else ""
        nt = menu_font.render(username + cursor, True, TEXT_BRIGHT)
        surf.blit(nt, (box_x + 12, box_y + box_h//2 - nt.get_height()//2))

        # Char count
        cc = desc_font.render(f"{len(username)}/{MAX_LEN}", True, TEXT_DIM)
        surf.blit(cc, (box_x + box_w - cc.get_width() - 8, box_y + box_h + 6))

        # Confirm button
        can_confirm = len(username.strip()) > 0
        btn_w, btn_h = 180, 38
        btn_r = pygame.Rect(sw//2 - btn_w//2, py + 150, btn_w, btn_h)
        btn_hov = btn_r.collidepoint(mx, my)
        if can_confirm:
            c = (57, 255, 20) if btn_hov else (40, 180, 20)
            pygame.draw.rect(surf, (10, 25, 12), btn_r, 0, border_radius=6)
            pygame.draw.rect(surf, c, btn_r, 1 if not btn_hov else 2, border_radius=6)
            bt = menu_font.render("Confirm", True, (57, 255, 20))
        else:
            pygame.draw.rect(surf, (15, 17, 28), btn_r, 0, border_radius=6)
            pygame.draw.rect(surf, BORDER, btn_r, 1, border_radius=6)
            bt = menu_font.render("Confirm", True, TEXT_DIM)
        surf.blit(bt, (btn_r.centerx - bt.get_width()//2, btn_r.centery - bt.get_height()//2))

        # Escape hint
        eh = desc_font.render("ESC to cancel  |  Enter to confirm", True, TEXT_DIM)
        surf.blit(eh, (sw//2 - eh.get_width()//2, py + ph - 24))

        display_mgr.present()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if username.strip():
                        gs.local_username = username.strip()
                        _save_username(gs.local_username)
                        return gs.local_username
                elif event.key == pygame.K_BACKSPACE:
                    username = username[:-1]
                elif event.key == pygame.K_ESCAPE:
                    if not username.strip():
                        username = "Player"
                    gs.local_username = username.strip()
                    _save_username(gs.local_username)
                    return gs.local_username
                elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    try:
                        if not pygame.scrap.get_init(): pygame.scrap.init()
                        clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if clip:
                            text = clip.decode("utf-8", errors="ignore").replace("\x00", "").strip()
                            username += text[:MAX_LEN - len(username)]
                    except: pass
                else:
                    if len(username) < MAX_LEN and event.unicode.isprintable():
                        username += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_r.collidepoint(event.pos) and username.strip():
                    gs.local_username = username.strip()
                    _save_username(gs.local_username)
                    return gs.local_username

        clock.tick(settings_module.FPS or 0)