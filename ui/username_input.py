# username_input.py
"""Username entry screen."""

import pygame
import sys
import core.settings as settings_module
from core.settings import *
from core.game_state import (
    display_mgr, clock, gs,
    header_font, title_font, menu_font, small_font
)


def _save_username(name):
    """Persist username into config.json."""
    settings_module.config["username"] = name
    settings_module.save_config(settings_module.config)


def show_username_input():
    """Ask the player to enter a username. Returns the username string."""
    username = gs.local_username
    MAX_LEN = 16

    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BLACK)

        title = header_font.render("ENTER USERNAME", True, CYAN)
        surf.blit(title, (sw // 2 - title.get_width() // 2, sh // 4 - 30))

        hint = small_font.render("Your name will be shown above your character.", True, GRAY)
        surf.blit(hint, (sw // 2 - hint.get_width() // 2, sh // 4 + 35))

        box_w, box_h = 400, 55
        box_x = sw // 2 - box_w // 2
        box_y = sh // 2 - box_h // 2 - 20
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(surf, DARK_GRAY, box_rect)
        pygame.draw.rect(surf, GOLD, box_rect, 3)

        display_text = username + ("|" if (pygame.time.get_ticks() // 500) % 2 == 0 else "")
        name_txt = title_font.render(display_text, True, WHITE)
        surf.blit(name_txt, (box_x + 15, box_y + box_h // 2 - name_txt.get_height() // 2))

        char_count = small_font.render(f"{len(username)}/{MAX_LEN}", True, GRAY)
        surf.blit(char_count, (box_x + box_w - char_count.get_width() - 8, box_y + box_h + 6))

        btn_w, btn_h = 200, 45
        btn_x = sw // 2 - btn_w // 2
        btn_y = sh // 2 + 60
        confirm_btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        can_confirm = len(username.strip()) > 0
        btn_color = GRAY if (can_confirm and confirm_btn.collidepoint(mx, my)) else DARK_GRAY
        border_color = GREEN if can_confirm else DARK_GRAY
        pygame.draw.rect(surf, btn_color, confirm_btn)
        pygame.draw.rect(surf, border_color, confirm_btn, 3)
        btn_txt = menu_font.render("Confirm", True, GREEN if can_confirm else GRAY)
        surf.blit(btn_txt, (confirm_btn.centerx - btn_txt.get_width() // 2,
                            confirm_btn.centery - btn_txt.get_height() // 2))

        pygame.display.flip()

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
                        if not pygame.scrap.get_init():
                            pygame.scrap.init()
                        clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if clip:
                            text = clip.decode("utf-8", errors="ignore").replace("\x00", "").strip()
                            remaining = MAX_LEN - len(username)
                            username += text[:remaining]
                    except Exception:
                        pass
                else:
                    if len(username) < MAX_LEN and event.unicode.isprintable():
                        username += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN:
                if confirm_btn.collidepoint(event.pos) and username.strip():
                    gs.local_username = username.strip()
                    _save_username(gs.local_username)
                    return gs.local_username

        clock.tick(60)