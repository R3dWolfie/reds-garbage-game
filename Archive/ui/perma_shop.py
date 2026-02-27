# perma_shop.py
"""Permanent upgrade shop — vertical layout, category sidebar, no flicker."""

import pygame
import sys
import math
import core.settings as settings_module
from core.settings import *
from core.game_state import (
    display_mgr, clock, sounds,
    header_font, title_font, menu_font, small_font, desc_font
)
from game.helpers import spend_gold

# ── Shared colors (match global standards) ──
ACCENT = (0, 200, 255)
BG_DARK = (5, 6, 16)
PANEL_BG = (10, 12, 24)
TEXT_DIM = (60, 65, 80)
TEXT_MID = (130, 140, 160)
TEXT_BRIGHT = (220, 225, 240)
BORDER = (35, 40, 60)

SHOP_CATEGORIES = [
    ("VACUUMBOTS", (0, 200, 220), ["roomba_count", "roomba_speed", "roomba_range", "roomba_damage"]),
    ("SAWS", (180, 190, 210), ["saw_count", "saw_damage", "saw_speed", "saw_size"]),
    ("OFFENSE", (255, 80, 80), ["crit_chance", "fire_rate_boost", "bullet_ricochet", "thorns"]),
    ("DEFENSE", (70, 160, 255), ["armor", "starting_hp", "revival", "health_regen", "dodge_chance", "shield"]),
    ("MOBILITY", (80, 220, 180), ["dash_power", "move_speed"]),
    ("UTILITY", (160, 100, 240), ["base_magnet", "gold_magnet", "xp_bonus"]),
    ("ECONOMY", (255, 200, 50), ["gold_rush", "lucky_drops"]),
]

_ITEM_MAP = {item["key"]: item for item in PERMA_SHOP_ITEMS}


def _draw_icon(surf, key, cx, cy, size, color):
    """Draw a themed icon for each upgrade."""
    r = size // 2
    if "roomba" in key:
        pygame.draw.circle(surf, color, (cx, cy), r)
        pygame.draw.circle(surf, (0, 60, 70), (cx, cy), r, 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx + 3, cy - 2), 3)
    elif "saw" in key:
        pygame.draw.circle(surf, color, (cx, cy), r - 2)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            tx = cx + int((r + 1) * math.cos(rad))
            ty = cy + int((r + 1) * math.sin(rad))
            pygame.draw.circle(surf, (255, 255, 255), (tx, ty), 2)
        pygame.draw.circle(surf, (50, 50, 60), (cx, cy), 3)
    elif key == "crit_chance":
        pts = [(cx - 2, cy - r + 2), (cx + 1, cy - 1), (cx - 1, cy), (cx + 3, cy + r - 2)]
        pygame.draw.lines(surf, color, False, pts, 2)
    elif key in ("armor", "shield"):
        pts = [(cx, cy - r + 2), (cx + r - 2, cy - 2), (cx + r - 3, cy + 2),
               (cx, cy + r - 1), (cx - r + 3, cy + 2), (cx - r + 2, cy - 2)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, (255, 255, 255), pts, 1)
    elif key in ("starting_hp", "health_regen"):
        pygame.draw.circle(surf, color, (cx - 3, cy - 2), 4)
        pygame.draw.circle(surf, color, (cx + 3, cy - 2), 4)
        pygame.draw.polygon(surf, color, [(cx - 7, cy - 1), (cx, cy + r - 1), (cx + 7, cy - 1)])
    elif key == "revival":
        pygame.draw.rect(surf, color, (cx - 2, cy - r + 3, 5, r * 2 - 6))
        pygame.draw.rect(surf, color, (cx - r + 3, cy - 2, r * 2 - 6, 5))
    elif key in ("gold_rush", "lucky_drops"):
        for i in range(3):
            oy = cy + 3 - i * 4
            pygame.draw.ellipse(surf, color, (cx - r + 3, oy - 2, (r - 3) * 2, 6))
    elif key in ("base_magnet", "gold_magnet"):
        pygame.draw.arc(surf, color, (cx - r + 2, cy - 2, (r - 2) * 2, r), 0, math.pi, 3)
    elif key == "xp_bonus":
        pts = [(cx, cy - r + 2), (cx + 3, cy - 1), (cx + r - 1, cy),
               (cx + 3, cy + 1), (cx, cy + r - 2), (cx - 3, cy + 1),
               (cx - r + 1, cy), (cx - 3, cy - 1)]
        pygame.draw.polygon(surf, color, pts)
    elif key == "dash_power":
        pygame.draw.polygon(surf, color, [(cx + r - 2, cy), (cx - 2, cy - r + 3), (cx - 2, cy + r - 3)])
    elif key == "move_speed":
        pygame.draw.ellipse(surf, color, (cx - r + 3, cy - 2, r * 2 - 6, r - 2))
    elif key == "fire_rate_boost":
        pygame.draw.circle(surf, color, (cx - 3, cy - 3), 3)
        pygame.draw.circle(surf, color, (cx + 3, cy + 1), 3)
    elif key == "bullet_ricochet":
        pts = [(cx - r + 3, cy - r + 4), (cx, cy), (cx + r - 3, cy - 3)]
        pygame.draw.lines(surf, color, False, pts, 2)
    elif key == "thorns":
        for a in range(0, 360, 30):
            rad = math.radians(a)
            ix, iy = cx + int((r-4)*math.cos(rad)), cy + int((r-4)*math.sin(rad))
            ox, oy = cx + int(r*math.cos(rad)), cy + int(r*math.sin(rad))
            pygame.draw.line(surf, color, (ix, iy), (ox, oy), 2)
    elif key == "dodge_chance":
        pygame.draw.ellipse(surf, color, (cx-r+2, cy-r+2, (r-2)*2, (r-2)*2), 2)
    else:
        pygame.draw.rect(surf, color, (cx - r + 2, cy - r + 2, size - 4, size - 4))


def _back_btn(surf, mx, my):
    r = pygame.Rect(16, 16, 90, 34)
    hov = r.collidepoint(mx, my)
    c = ACCENT if hov else TEXT_DIM
    pygame.draw.rect(surf, c, r, 1 if not hov else 2, border_radius=5)
    t = small_font.render("< Back", True, TEXT_BRIGHT if hov else TEXT_MID)
    surf.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))
    return r


def show_perma_shop():
    """Permanent upgrade shop — vertical sidebar layout."""
    scroll_y = 0
    selected_cat = 0

    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)

        # ── Back button (top-left, universal) ──
        back_r = _back_btn(surf, mx, my)

        # ── Gold display (top-right) ──
        current_gold = settings_module.config.get("gold", 0)
        gt = menu_font.render(f"{current_gold}g", True, (255, 215, 0))
        surf.blit(gt, (sw - gt.get_width() - 24, 20))
        gl = small_font.render("Gold", True, TEXT_DIM)
        surf.blit(gl, (sw - gt.get_width() - gl.get_width() - 32, 23))

        # ── Title ──
        tt = title_font.render("SHOP", True, TEXT_BRIGHT)
        surf.blit(tt, (sw//2 - tt.get_width()//2, 12))

        # ── Layout ──
        sidebar_w = 180
        sidebar_x = 20
        sidebar_top = 60
        content_x = sidebar_x + sidebar_w + 16
        content_y = 60
        content_w = sw - content_x - 20
        content_h = sh - content_y - 20

        # ── Category sidebar ──
        cat_rects = []
        for i, (cat_label, cat_color, _) in enumerate(SHOP_CATEGORIES):
            r = pygame.Rect(sidebar_x, sidebar_top + i * 42, sidebar_w, 36)
            cat_rects.append(r)
            is_sel = (i == selected_cat)
            hov = r.collidepoint(mx, my)

            if is_sel:
                pygame.draw.rect(surf, (15, 20, 38), r, 0, border_radius=6)
                pygame.draw.rect(surf, cat_color, r, 2, border_radius=6)
            elif hov:
                pygame.draw.rect(surf, (18, 22, 38), r, 0, border_radius=6)
                pygame.draw.rect(surf, cat_color, r, 1, border_radius=6)
            else:
                pygame.draw.rect(surf, (12, 14, 26), r, 0, border_radius=6)
                pygame.draw.rect(surf, BORDER, r, 1, border_radius=6)

            pygame.draw.circle(surf, cat_color, (r.x + 16, r.centery), 4)
            ct = small_font.render(cat_label, True, cat_color if is_sel else TEXT_MID)
            surf.blit(ct, (r.x + 28, r.centery - ct.get_height()//2))

        # Scroll hint
        hint = desc_font.render("Click category or scroll items", True, TEXT_DIM)
        surf.blit(hint, (sidebar_x + 4, sidebar_top + len(SHOP_CATEGORIES) * 42 + 10))

        # ── Content area ──
        cat_label, cat_color, cat_keys = SHOP_CATEGORIES[selected_cat]
        cat_items = [_ITEM_MAP[k] for k in cat_keys if k in _ITEM_MAP]
        perma = settings_module.config.get("perma_upgrades", {})

        card_w = min(content_w, 520)
        card_h = 82
        card_gap = 10
        card_x = content_x + (content_w - card_w) // 2

        total_h = len(cat_items) * (card_h + card_gap)
        max_scroll = max(0, total_h - content_h + 20)
        scroll_y = max(0, min(scroll_y, max_scroll))

        item_rects = []
        for i, item in enumerate(cat_items):
            cy = content_y + i * (card_h + card_gap) - scroll_y
            card_rect = pygame.Rect(card_x, cy, card_w, card_h)
            item_rects.append((card_rect, item))

            if cy + card_h < content_y - 5 or cy > sh:
                continue

            current_level = perma.get(item["key"], 0)
            max_level = item["max_level"]
            is_maxed = current_level >= max_level
            cost = item["costs"][current_level] if not is_maxed else 0
            can_afford = current_gold >= cost and not is_maxed
            hov = card_rect.collidepoint(mx, my) and cy >= content_y - 5

            # Card bg
            if is_maxed:
                pygame.draw.rect(surf, (8, 16, 12), card_rect, 0, border_radius=8)
                border_c = (50, 180, 20)
            elif hov:
                pygame.draw.rect(surf, (18, 22, 40), card_rect, 0, border_radius=8)
                border_c = cat_color
            else:
                pygame.draw.rect(surf, (12, 14, 26), card_rect, 0, border_radius=8)
                border_c = BORDER

            pygame.draw.rect(surf, border_c, card_rect, 1 if not hov else 2, border_radius=8)

            # Left accent
            pygame.draw.rect(surf, cat_color, (card_x, cy + 6, 3, card_h - 12), border_radius=2)

            # Icon (larger, colored to match category)
            _draw_icon(surf, item["key"], card_x + 30, cy + card_h//2, 34, cat_color)

            # Name
            name_x = card_x + 56
            nt = menu_font.render(item["name"], True, TEXT_BRIGHT if not is_maxed else (57, 200, 20))
            surf.blit(nt, (name_x, cy + 8))

            # Description
            desc_str = item["desc"]
            if len(desc_str) > 55:
                desc_str = desc_str[:52] + "..."
            dt = desc_font.render(desc_str, True, TEXT_DIM)
            surf.blit(dt, (name_x, cy + 30))

            # Stat per level
            st = desc_font.render(item["stat_per_level"], True, cat_color)
            surf.blit(st, (name_x, cy + 48))

            # Level pips (right side, compact)
            pip_area_x = card_x + card_w - 130
            pip_y_base = cy + 8
            pips_row = min(max_level, 10)
            for p in range(max_level):
                row = p // pips_row
                col = p % pips_row
                px = pip_area_x + col * 10
                py = pip_y_base + row * 8
                filled = p < current_level
                pygame.draw.rect(surf, cat_color if filled else (25, 28, 42),
                                 (px, py, 7, 5), border_radius=1)
                if not filled:
                    pygame.draw.rect(surf, (40, 45, 60), (px, py, 7, 5), 1, border_radius=1)

            # Buy / MAXED
            btn_x = card_x + card_w - 78
            btn_y2 = cy + card_h - 30
            btn_w2 = 68
            btn_h2 = 22

            if is_maxed:
                mt = small_font.render("MAX", True, (57, 200, 20))
                surf.blit(mt, (btn_x + btn_w2//2 - mt.get_width()//2, btn_y2 + 2))
            else:
                buy_r = pygame.Rect(btn_x, btn_y2, btn_w2, btn_h2)
                buy_hov = buy_r.collidepoint(mx, my)
                if can_afford:
                    c2 = (40, 160, 20) if not buy_hov else (57, 200, 20)
                    pygame.draw.rect(surf, (10, 25, 10), buy_r, 0, border_radius=4)
                    pygame.draw.rect(surf, c2, buy_r, 1 if not buy_hov else 2, border_radius=4)
                    ct2 = small_font.render(f"{cost}g", True, (57, 255, 20))
                else:
                    pygame.draw.rect(surf, (20, 15, 15), buy_r, 0, border_radius=4)
                    pygame.draw.rect(surf, (60, 35, 35), buy_r, 1, border_radius=4)
                    ct2 = small_font.render(f"{cost}g", True, (80, 50, 50))
                surf.blit(ct2, (buy_r.centerx - ct2.get_width()//2,
                                buy_r.centery - ct2.get_height()//2))

        # Scroll bar
        if max_scroll > 0:
            bar_total = content_h
            bar_h = max(20, int(bar_total * content_h / (total_h + 1)))
            bar_y = content_y + int(scroll_y / max_scroll * (bar_total - bar_h))
            pygame.draw.rect(surf, (25, 28, 42), (sw - 14, content_y, 5, bar_total), border_radius=3)
            pygame.draw.rect(surf, ACCENT, (sw - 14, bar_y, 5, bar_h), border_radius=3)

        display_mgr.present()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * 40
                scroll_y = max(0, min(scroll_y, max_scroll))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_r.collidepoint(event.pos):
                    return
                for i, r in enumerate(cat_rects):
                    if r.collidepoint(event.pos):
                        selected_cat = i
                        scroll_y = 0
                for card_rect, item in item_rects:
                    if card_rect.collidepoint(event.pos) and card_rect.y >= content_y - 5:
                        cl = perma.get(item["key"], 0)
                        if cl < item["max_level"]:
                            c_val = item["costs"][cl]
                            if spend_gold(c_val):
                                perma[item["key"]] = cl + 1
                                settings_module.config["perma_upgrades"] = perma
                                settings_module.save_config(settings_module.config)
                                sounds.play_gem()

        clock.tick(settings_module.FPS or 0)