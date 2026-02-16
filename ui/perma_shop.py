# perma_shop.py
"""Permanent upgrade shop - spend gold on persistent upgrades. Neon themed, categorized."""

import pygame
import sys
import math
import core.settings as settings_module
from core.settings import *
from core.game_state import (
    display_mgr, clock, sounds,
    header_font, title_font, menu_font, small_font
)
from game.helpers import spend_gold

_shop_time = 0.0

# Category definitions: (label, neon_color, list of item keys)
SHOP_CATEGORIES = [
    ("ROOMBAS", (0, 255, 255), ["roomba_count", "roomba_speed", "roomba_range", "roomba_damage"]),
    ("SAWS", (200, 200, 220), ["saw_count", "saw_damage", "saw_speed", "saw_size"]),
    ("OFFENSE", (255, 80, 80), ["crit_chance", "fire_rate_boost", "bullet_ricochet", "thorns"]),
    ("DEFENSE", (70, 180, 255), ["armor", "starting_hp", "revival", "health_regen", "dodge_chance", "shield"]),
    ("MOBILITY", (100, 255, 200), ["dash_power", "move_speed"]),
    ("UTILITY", (180, 100, 255), ["base_magnet", "gold_magnet", "xp_bonus"]),
    ("ECONOMY", (255, 215, 0), ["gold_rush", "lucky_drops"]),
]

# Build a quick lookup: key -> item dict
_ITEM_MAP = {item["key"]: item for item in PERMA_SHOP_ITEMS}


def _draw_icon(surf, key, cx, cy, size, color):
    """Draw a small themed icon for each upgrade type."""
    r = size // 2
    if key == "roomba_count":
        # Little roomba circle with eye
        pygame.draw.circle(surf, color, (cx, cy), r)
        pygame.draw.circle(surf, (0, 80, 90), (cx, cy), r, 2)
        pygame.draw.circle(surf, WHITE, (cx + 3, cy - 2), 3)
        pygame.draw.circle(surf, (0, 40, 50), (cx + 4, cy - 2), 1)
    elif key == "roomba_speed":
        # Speedlines + circle
        pygame.draw.circle(surf, color, (cx, cy), r - 2)
        for i in range(3):
            y = cy - 4 + i * 4
            pygame.draw.line(surf, (255, 255, 255), (cx - r - 3, y), (cx - r + 3, y), 1)
    elif key == "roomba_range":
        # Circle with expanding rings
        pygame.draw.circle(surf, color, (cx, cy), r - 4)
        pygame.draw.circle(surf, (*color, 120), (cx, cy), r - 1, 1)
        pygame.draw.circle(surf, (*color, 60), (cx, cy), r + 2, 1)
    elif key == "saw_count":
        # Saw blade - circle with teeth
        pygame.draw.circle(surf, color, (cx, cy), r - 2)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            tx = cx + int((r + 1) * math.cos(rad))
            ty = cy + int((r + 1) * math.sin(rad))
            pygame.draw.circle(surf, WHITE, (tx, ty), 2)
        pygame.draw.circle(surf, (60, 60, 70), (cx, cy), 3)
    elif key == "saw_damage":
        # Blade with spark
        pygame.draw.circle(surf, color, (cx, cy), r - 2)
        pygame.draw.line(surf, (255, 255, 100), (cx - 2, cy - r + 1), (cx + 4, cy - r - 3), 2)
        pygame.draw.line(surf, (255, 255, 100), (cx + 2, cy - r + 1), (cx - 2, cy - r - 3), 2)
    elif key == "saw_speed":
        # Spinning arrow
        pygame.draw.circle(surf, color, (cx, cy), r - 3, 2)
        pygame.draw.line(surf, WHITE, (cx + r - 4, cy - 2), (cx + r - 1, cy), 2)
        pygame.draw.line(surf, WHITE, (cx + r - 4, cy + 2), (cx + r - 1, cy), 2)
    elif key == "crit_chance":
        # Lightning bolt
        pts = [(cx - 2, cy - r + 2), (cx + 1, cy - 1), (cx - 1, cy), (cx + 3, cy + r - 2)]
        pygame.draw.lines(surf, color, False, pts, 2)
        pygame.draw.circle(surf, (255, 255, 200), (cx + 3, cy + r - 2), 2)
    elif key == "base_magnet":
        # Magnet U-shape
        pygame.draw.arc(surf, color, (cx - r + 2, cy - 2, (r - 2) * 2, r), 0, math.pi, 3)
        pygame.draw.line(surf, (255, 80, 80), (cx - r + 2, cy - 1), (cx - r + 2, cy - r + 3), 3)
        pygame.draw.line(surf, (80, 80, 255), (cx + r - 3, cy - 1), (cx + r - 3, cy - r + 3), 3)
    elif key == "gold_magnet":
        # Coin with magnet lines
        pygame.draw.circle(surf, color, (cx, cy), r - 2)
        pygame.draw.circle(surf, (200, 170, 0), (cx, cy), r - 4)
        pygame.draw.line(surf, WHITE, (cx - r, cy), (cx - r + 3, cy), 1)
        pygame.draw.line(surf, WHITE, (cx + r - 3, cy), (cx + r, cy), 1)
    elif key == "armor":
        # Shield shape
        pts = [(cx, cy - r + 2), (cx + r - 2, cy - 2), (cx + r - 3, cy + 2),
               (cx, cy + r - 1), (cx - r + 3, cy + 2), (cx - r + 2, cy - 2)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)
    elif key == "xp_bonus":
        # Star / XP gem
        pts = [(cx, cy - r + 2), (cx + 3, cy - 1), (cx + r - 1, cy),
               (cx + 3, cy + 1), (cx, cy + r - 2), (cx - 3, cy + 1),
               (cx - r + 1, cy), (cx - 3, cy - 1)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, (255, 255, 255), pts, 1)
    elif key == "starting_hp":
        # Heart
        pygame.draw.circle(surf, color, (cx - 3, cy - 2), 4)
        pygame.draw.circle(surf, color, (cx + 3, cy - 2), 4)
        pts = [(cx - 7, cy - 1), (cx, cy + r - 1), (cx + 7, cy - 1)]
        pygame.draw.polygon(surf, color, pts)
    elif key == "gold_rush":
        # Gold coins stack
        for i in range(3):
            oy = cy + 3 - i * 4
            pygame.draw.ellipse(surf, color, (cx - r + 3, oy - 2, (r - 3) * 2, 6))
            pygame.draw.ellipse(surf, (200, 170, 0), (cx - r + 3, oy - 2, (r - 3) * 2, 6), 1)
    elif key == "revival":
        # Plus / cross (medic)
        pygame.draw.rect(surf, color, (cx - 2, cy - r + 3, 5, r * 2 - 6))
        pygame.draw.rect(surf, color, (cx - r + 3, cy - 2, r * 2 - 6, 5))
        pygame.draw.rect(surf, WHITE, (cx - 2, cy - r + 3, 5, r * 2 - 6), 1)
        pygame.draw.rect(surf, WHITE, (cx - r + 3, cy - 2, r * 2 - 6, 5), 1)
    elif key == "dash_power":
        # Arrow/dash streaks
        pygame.draw.polygon(surf, color, [(cx + r - 2, cy), (cx - 2, cy - r + 3), (cx - 2, cy + r - 3)])
        for i in range(3):
            lx = cx - 4 - i * 4
            pygame.draw.line(surf, (*color, 180), (lx, cy - 2), (lx - 3, cy - 2), 2)
            pygame.draw.line(surf, (*color, 180), (lx, cy + 2), (lx - 3, cy + 2), 2)
    elif key == "health_regen":
        # Heart with pulse wave
        pygame.draw.circle(surf, color, (cx - 3, cy - 1), 4)
        pygame.draw.circle(surf, color, (cx + 3, cy - 1), 4)
        pygame.draw.polygon(surf, color, [(cx - 7, cy), (cx, cy + r - 2), (cx + 7, cy)])
        # Tiny pulse line
        pts = [(cx - r, cy + r - 3), (cx - 3, cy + r - 3), (cx, cy + r - 7), (cx + 3, cy + r - 3), (cx + r, cy + r - 3)]
        pygame.draw.lines(surf, (255, 255, 255), False, pts, 1)
    elif key == "dodge_chance":
        # Ghost/phase outline
        pygame.draw.ellipse(surf, (*color, 80), (cx - r + 2, cy - r + 2, (r - 2) * 2, (r - 2) * 2))
        pygame.draw.ellipse(surf, color, (cx - r + 2, cy - r + 2, (r - 2) * 2, (r - 2) * 2), 2)
        # Dashed inner
        for a in range(0, 360, 60):
            rad = math.radians(a)
            px = cx + int((r - 5) * math.cos(rad))
            py_val = cy + int((r - 5) * math.sin(rad))
            pygame.draw.circle(surf, WHITE, (px, py_val), 1)
    elif key == "thorns":
        # Spiky ring
        for a in range(0, 360, 30):
            rad = math.radians(a)
            inner = r - 4
            outer = r
            ix = cx + int(inner * math.cos(rad))
            iy = cy + int(inner * math.sin(rad))
            ox = cx + int(outer * math.cos(rad))
            oy = cy + int(outer * math.sin(rad))
            pygame.draw.line(surf, color, (ix, iy), (ox, oy), 2)
        pygame.draw.circle(surf, (*color, 80), (cx, cy), r - 5)
    elif key == "move_speed":
        # Running shoe / wind lines
        pygame.draw.ellipse(surf, color, (cx - r + 3, cy - 2, r * 2 - 6, r - 2))
        pygame.draw.line(surf, WHITE, (cx - r + 4, cy + r // 2 - 3), (cx + r - 4, cy + r // 2 - 3), 1)
        for i in range(3):
            lx = cx - r + 1
            ly = cy - 4 + i * 4
            pygame.draw.line(surf, (*color, 150), (lx, ly), (lx - 4, ly), 1)
    elif key == "fire_rate_boost":
        # Double bullet
        pygame.draw.circle(surf, color, (cx - 3, cy - 3), 3)
        pygame.draw.circle(surf, color, (cx + 3, cy + 1), 3)
        pygame.draw.circle(surf, (255, 255, 200), (cx - 3, cy - 3), 1)
        pygame.draw.circle(surf, (255, 255, 200), (cx + 3, cy + 1), 1)
    elif key == "bullet_ricochet":
        # Bouncing arrow
        pts = [(cx - r + 3, cy - r + 4), (cx, cy), (cx + r - 3, cy - 3)]
        pygame.draw.lines(surf, color, False, pts, 2)
        # Arrow tip
        pygame.draw.line(surf, color, (cx + r - 3, cy - 3), (cx + r - 6, cy - 6), 2)
        pygame.draw.line(surf, color, (cx + r - 3, cy - 3), (cx + r - 1, cy - 7), 2)
        # Bounce dot
        pygame.draw.circle(surf, WHITE, (cx, cy), 2)
    elif key == "saw_size":
        # Big saw blade
        pygame.draw.circle(surf, color, (cx, cy), r - 1)
        for angle in range(0, 360, 40):
            rad = math.radians(angle)
            tx = cx + int(r * math.cos(rad))
            ty = cy + int(r * math.sin(rad))
            pygame.draw.circle(surf, WHITE, (tx, ty), 2)
        pygame.draw.circle(surf, (60, 60, 70), (cx, cy), 4)
    elif key == "shield":
        # Shield bubble
        pygame.draw.circle(surf, (*color, 50), (cx, cy), r - 1)
        pygame.draw.circle(surf, color, (cx, cy), r - 1, 2)
        pygame.draw.arc(surf, WHITE, (cx - r + 4, cy - r + 4, (r - 4) * 2, (r - 4) * 2),
                         0.5, 1.8, 2)
    elif key == "lucky_drops":
        # Four-leaf clover / star
        for a in [0, 90, 180, 270]:
            rad = math.radians(a)
            lx = cx + int(5 * math.cos(rad))
            ly = cy + int(5 * math.sin(rad))
            pygame.draw.circle(surf, color, (lx, ly), 4)
        pygame.draw.circle(surf, (255, 255, 200), (cx, cy), 2)
    elif key == "roomba_damage":
        # Roomba with lightning
        pygame.draw.circle(surf, (0, 255, 255), (cx, cy), r - 3)
        pygame.draw.circle(surf, (0, 80, 90), (cx, cy), r - 3, 2)
        # Zap bolt
        pts = [(cx + 1, cy - r + 3), (cx - 2, cy), (cx + 2, cy), (cx - 1, cy + r - 3)]
        pygame.draw.lines(surf, (255, 255, 100), False, pts, 2)
    else:
        # Fallback square
        pygame.draw.rect(surf, color, (cx - r + 2, cy - r + 2, size - 4, size - 4))


def _wrap_text(text, font_obj, max_width):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split(' ')
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        if font_obj.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def show_perma_shop():
    """Permanent upgrade shop - spend gold on persistent upgrades."""
    global _shop_time
    scroll_offset = 0
    max_scroll = 0

    while True:
        _shop_time += 0.03
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill((5, 5, 15))

        # Subtle hex background
        hex_r = 60
        hex_w = int(hex_r * math.sqrt(3))
        for row in range(-1, sh // int(hex_r * 1.5) + 3):
            for col in range(-1, sw // hex_w + 3):
                x = col * hex_w + (row % 2) * (hex_w // 2)
                y = row * int(hex_r * 1.5)
                phase = (col * 0.3 + row * 0.5) % (2 * math.pi)
                pulse = math.sin(_shop_time + phase) * 0.5 + 0.5
                c = int(5 + pulse * 10)
                points = []
                for k in range(6):
                    a = math.radians(60 * k - 30)
                    points.append((x + hex_r * math.cos(a), y + hex_r * math.sin(a)))
                pygame.draw.polygon(surf, (c, c + 2, c + 8), points, 1)

        # Title
        title = header_font.render("SHOP", True, GOLD)
        glow = pygame.Surface((title.get_width() + 20, title.get_height() + 10))
        glow.fill((255, 215, 0))
        glow.set_alpha(15)
        surf.blit(glow, (sw // 2 - glow.get_width() // 2, 10))
        surf.blit(title, (sw // 2 - title.get_width() // 2, 15))

        # Gold display
        current_gold = settings_module.config.get("gold", 0)
        gold_pulse = math.sin(_shop_time * 2) * 0.15 + 0.85
        gold_color = (int(255 * gold_pulse), int(215 * gold_pulse), 0)
        gold_txt = title_font.render(f"Gold: {current_gold}", True, gold_color)
        surf.blit(gold_txt, (sw // 2 - gold_txt.get_width() // 2, 60))

        perma = settings_module.config.get("perma_upgrades", {})

        # Layout constants
        card_w = 230
        card_h = 155
        card_gap = 12
        cat_header_h = 32
        section_gap = 10
        left_margin = 40
        content_start_y = 100

        # Calculate layout and draw categories
        y_cursor = content_start_y + scroll_offset
        item_rects = []  # (rect, item_dict)

        for cat_label, cat_color, cat_keys in SHOP_CATEGORIES:
            cat_items = [_ITEM_MAP[k] for k in cat_keys if k in _ITEM_MAP]
            if not cat_items:
                continue

            # Category header
            header_y = y_cursor
            if content_start_y - 10 < header_y < sh:
                # Header line
                pygame.draw.line(surf, (*cat_color, 80), (left_margin, header_y + cat_header_h - 4),
                                 (sw - left_margin, header_y + cat_header_h - 4), 1)
                cat_txt = menu_font.render(cat_label, True, cat_color)
                surf.blit(cat_txt, (left_margin + 5, header_y + 4))

            y_cursor += cat_header_h + 4

            # Cards in a row
            cards_per_row = max(1, (sw - left_margin * 2 + card_gap) // (card_w + card_gap))
            for i, item in enumerate(cat_items):
                col = i % cards_per_row
                row = i // cards_per_row
                cx = left_margin + col * (card_w + card_gap)
                cy = y_cursor + row * (card_h + card_gap)

                card_rect = pygame.Rect(cx, cy, card_w, card_h)
                item_rects.append((card_rect, item))

                if cy + card_h < content_start_y - 10 or cy > sh:
                    continue

                current_level = perma.get(item["key"], 0)
                max_level = item["max_level"]
                is_maxed = current_level >= max_level
                cost = item["costs"][current_level] if not is_maxed else 0
                can_afford = current_gold >= cost and not is_maxed

                hovered = card_rect.collidepoint(mx, my) and cy >= content_start_y - 10

                # Card bg
                if is_maxed:
                    bg_alpha = 25
                    border_col = (57, 255, 20)
                elif hovered and can_afford:
                    bg_alpha = 45
                    border_col = GOLD
                elif hovered:
                    bg_alpha = 35
                    border_col = (255, 50, 80)
                else:
                    bg_alpha = 12
                    border_col = (50, 60, 75)

                card_bg = pygame.Surface((card_w, card_h))
                card_bg.fill(cat_color[:3])
                card_bg.set_alpha(bg_alpha)
                surf.blit(card_bg, (cx, cy))

                # Border with subtle glow
                if hovered:
                    for gi in range(4, 0, -1):
                        a = int(12 * (gi / 4))
                        pygame.draw.rect(surf, (*border_col[:3], a),
                                         (cx - gi, cy - gi, card_w + gi * 2, card_h + gi * 2), 1)
                pygame.draw.rect(surf, border_col, card_rect, 2 if hovered else 1)

                # Icon (drawn shape)
                icon_cx = cx + 22
                icon_cy = cy + 22
                _draw_icon(surf, item["key"], icon_cx, icon_cy, 28, item["icon_color"])

                # Name
                name_txt = menu_font.render(item["name"], True, cat_color if not is_maxed else (57, 255, 20))
                surf.blit(name_txt, (cx + 42, cy + 6))

                # Level pips (multi-row for high level counts)
                pip_y = cy + 30
                pip_x_start = cx + 42
                pips_per_row = max(1, (card_w - 50) // 12)
                for p in range(max_level):
                    row = p // pips_per_row
                    col = p % pips_per_row
                    pip_x = pip_x_start + col * 12
                    py_off = pip_y + row * 9
                    pip_color = cat_color if p < current_level else (30, 30, 40)
                    pygame.draw.rect(surf, pip_color, (pip_x, py_off, 8, 5))
                    pygame.draw.rect(surf, (60, 60, 70), (pip_x, py_off, 8, 5), 1)
                pip_rows = max(1, (max_level + pips_per_row - 1) // pips_per_row)
                pip_bottom = pip_y + pip_rows * 9

                # Description (wrapped)
                desc_lines = _wrap_text(item["desc"], small_font, card_w - 16)
                for j, line in enumerate(desc_lines[:2]):  # Max 2 lines
                    dt = small_font.render(line, True, (140, 150, 165))
                    surf.blit(dt, (cx + 8, pip_bottom + 4 + j * 16))

                # Stat per level
                stat_txt = small_font.render(item["stat_per_level"], True, (0, 255, 255))
                surf.blit(stat_txt, (cx + 8, pip_bottom + 38))

                # Level text
                lvl_str = f"Lv {current_level}/{max_level}"
                lvl_color = (57, 255, 20) if is_maxed else (160, 170, 185)
                lvl_txt = small_font.render(lvl_str, True, lvl_color)
                surf.blit(lvl_txt, (cx + 8, pip_bottom + 56))

                # Buy button or MAXED
                if is_maxed:
                    mx_txt = menu_font.render("MAXED", True, (57, 255, 20))
                    surf.blit(mx_txt, (cx + card_w - mx_txt.get_width() - 10, cy + card_h - 32))
                else:
                    cost_str = f"{cost}g"
                    cost_color = GOLD if can_afford else (255, 50, 80)
                    buy_rect = pygame.Rect(cx + card_w - 75, cy + card_h - 38, 65, 28)
                    buy_bg = pygame.Surface((65, 28))
                    buy_hover = buy_rect.collidepoint(mx, my)
                    buy_bg.fill(cost_color[:3])
                    buy_bg.set_alpha(35 if buy_hover else 15)
                    surf.blit(buy_bg, buy_rect.topleft)
                    pygame.draw.rect(surf, cost_color, buy_rect, 2)
                    buy_label = menu_font.render(cost_str, True, cost_color)
                    surf.blit(buy_label, (buy_rect.centerx - buy_label.get_width() // 2,
                                          buy_rect.centery - buy_label.get_height() // 2))

            # Advance y_cursor past this category's rows
            rows_in_cat = max(1, (len(cat_items) + cards_per_row - 1) // cards_per_row)
            y_cursor += rows_in_cat * (card_h + card_gap) + section_gap

        # Total content height
        total_content_h = y_cursor - scroll_offset + 80
        max_scroll = min(0, sh - total_content_h - content_start_y + 40)

        # Back button
        btn_w, btn_h = 200, 45
        back_btn = pygame.Rect(sw // 2 - btn_w // 2, sh - 55, btn_w, btn_h)
        hovered_back = back_btn.collidepoint(mx, my)
        bb = pygame.Surface((btn_w, btn_h))
        bb.fill((255, 255, 255))
        bb.set_alpha(20 if hovered_back else 8)
        surf.blit(bb, back_btn.topleft)
        pygame.draw.rect(surf, (200, 200, 220), back_btn, 2 if hovered_back else 1)
        back_txt = menu_font.render("BACK", True, (200, 200, 220))
        surf.blit(back_txt, (back_btn.centerx - back_txt.get_width() // 2,
                              back_btn.centery - back_txt.get_height() // 2))

        display_mgr.present()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset += event.y * 35
                scroll_offset = max(max_scroll, min(0, scroll_offset))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_btn.collidepoint(event.pos):
                    return
                for card_rect, item in item_rects:
                    if card_rect.collidepoint(event.pos) and card_rect.y >= content_start_y - 10:
                        current_level = perma.get(item["key"], 0)
                        if current_level < item["max_level"]:
                            cost_val = item["costs"][current_level]
                            if spend_gold(cost_val):
                                perma[item["key"]] = current_level + 1
                                settings_module.config["perma_upgrades"] = perma
                                settings_module.save_config(settings_module.config)
                                sounds.play_gem()

        clock.tick(30)