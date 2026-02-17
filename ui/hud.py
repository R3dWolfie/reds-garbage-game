# hud.py
"""HUD and drawing functions for in-game UI with neon styling."""

import pygame
import math
import core.settings as settings_module
from core.settings import *
import core.game_state as _gs

def _font():      return _gs.font
def _small_font(): return _gs.small_font
def _title_font(): return _gs.title_font
def _boss_font():  return _gs.boss_font

# Animation timer for HUD effects
_hud_time = 0.0


def _neon_bar(surf, x, y, w, h, ratio, bar_color, border_color, glow=True):
    """Draw a neon-styled progress bar."""
    # Dark background
    pygame.draw.rect(surf, (15, 15, 25), (x, y, w, h))
    # Fill
    fill_w = int(w * max(0, min(1, ratio)))
    if fill_w > 0:
        # Gradient-ish fill
        fill_surf = pygame.Surface((fill_w, h), pygame.SRCALPHA)
        fill_surf.fill(bar_color)
        surf.blit(fill_surf, (x, y))
        # Bright edge on fill
        if fill_w > 2:
            pygame.draw.line(surf, (min(255, bar_color[0] + 80), min(255, bar_color[1] + 80), min(255, bar_color[2] + 80)),
                             (x + fill_w - 1, y + 1), (x + fill_w - 1, y + h - 2), 1)
    # Glow border
    if glow:
        glow_surf = pygame.Surface((w + 6, h + 6), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*border_color[:3], 20), (0, 0, w + 6, h + 6), 2)
        surf.blit(glow_surf, (x - 3, y - 3))
    # Crisp border
    pygame.draw.rect(surf, border_color, (x, y, w, h), 1)


def draw_upgrade_counters(surf, player_obj):
    sx, sy = 10, 150
    header = _font().render("UPGRADES", True, (0, 255, 255))
    surf.blit(header, (sx, sy - 24))
    # Underline
    pygame.draw.line(surf, (0, 255, 255), (sx, sy - 2), (sx + header.get_width(), sy - 2), 1)

    stat_display = [
        ("SPD", "speed", player_obj.stats["speed"]),
        ("RATE", "fire_rate", player_obj.stats["fire_rate"]),
        ("BSPD", "bullet_speed", player_obj.stats["bullet_speed"]),
        ("HP", "max_health", player_obj.stats["max_health"]),
        ("MULT", "multishot", player_obj.stats["multishot"]),
        ("DMG", "damage", player_obj.stats["damage"]),
        ("PIER", "piercing", player_obj.stats["piercing"]),
        ("MAG", "magnet", player_obj.get_magnet_radius()),
        ("SIZE", "bullet_size", f"{player_obj.stats.get('bullet_size', 1.0):.1f}x"),
        ("XP×", "xp_gain", f"{player_obj.stats.get('xp_gain', 1.0):.2f}x"),
        ("ACC", "accuracy", f"{player_obj.stats.get('accuracy', 1.0):.1f}x"),
    ]

    neon_colors = [(0, 255, 255), (57, 255, 20), (0, 150, 255), (255, 0, 200),
                   (180, 0, 255), (255, 100, 0), (255, 255, 0)]

    for i, (label, key, value) in enumerate(stat_display):
        count = player_obj.upgrade_counts.get(key, 0)
        if count > 0:
            color = neon_colors[i % len(neon_colors)]
        else:
            color = (60, 60, 70)
        text = _small_font().render(f"{label}: {value}  (x{count})", True, color)
        surf.blit(text, (sx, sy + (i * 18)))


def draw_ui(surf, player_obj, wave, enemy_group, net_mode=None, party_level=None, party_xp=None, party_xp_to_next=None,
            gold_this_run=0, revivals_remaining=0):
    global _hud_time
    _hud_time += 0.03
    sw = settings_module.SCREEN_WIDTH

    # XP Bar (full width, top)
    if net_mode in ("host", "client") and party_xp is not None:
        xp_to_next = max(1, party_xp_to_next)
        xp_ratio = party_xp / xp_to_next
        current_level = party_level
        current_xp_val = party_xp
    else:
        xp_to_next = max(1, player_obj.xp_to_next_level)
        xp_ratio = player_obj.current_xp / xp_to_next
        current_level = player_obj.level
        current_xp_val = player_obj.current_xp

    # Neon XP bar
    _neon_bar(surf, 0, 0, sw, 22, xp_ratio, (0, 80, 200), (0, 150, 255))
    # XP pulse effect at fill edge
    pulse_x = int(xp_ratio * sw)
    if pulse_x > 5:
        pulse_alpha = int(80 + math.sin(_hud_time * 4) * 40)
        pulse_surf = pygame.Surface((6, 22), pygame.SRCALPHA)
        pulse_surf.fill((100, 200, 255, pulse_alpha))
        surf.blit(pulse_surf, (pulse_x - 3, 0))

    xp_text = _font().render(f"LVL {current_level}  ({current_xp_val}/{xp_to_next})", True, (200, 230, 255))
    surf.blit(xp_text, (10, 24))

    # Health Bar with neon red
    hp_bar_w, hp_bar_h = 200, 20
    hp_x, hp_y = 10, 48
    max_hp = max(1, player_obj.stats["max_health"])
    hp_ratio = max(0, player_obj.current_health / max_hp)

    # Color shifts based on HP
    if hp_ratio > 0.5:
        bar_col = (0, 230, 100)
        border_col = (57, 255, 20)
    elif hp_ratio > 0.25:
        bar_col = (255, 165, 0)
        border_col = (255, 200, 0)
    else:
        bar_col = (255, 30, 60)
        border_col = (255, 50, 80)

    _neon_bar(surf, hp_x, hp_y, hp_bar_w, hp_bar_h, hp_ratio, bar_col, border_col)
    hp_str = f"{max(0, player_obj.current_health)} / {player_obj.stats['max_health']}"
    hp_text = _font().render(hp_str, True, WHITE)
    surf.blit(hp_text, (hp_x + hp_bar_w // 2 - hp_text.get_width() // 2,
                        hp_y + hp_bar_h // 2 - hp_text.get_height() // 2))

    # Quick Stats with neon
    crit_pct = int(getattr(player_obj, 'crit_chance', 0) * 100)
    quick = _font().render(
        f"DMG:{player_obj.stats['damage']}  PIERCE:{player_obj.stats['piercing']}  "
        f"MULTI:{player_obj.stats['multishot']}  MAG:{player_obj.get_magnet_radius()}px",
        True, (180, 220, 255))
    surf.blit(quick, (10, 76))

    class_txt = _small_font().render(f"Class: {player_obj.DISPLAY_NAME}", True, player_obj.SPRITE_COLOR)
    surf.blit(class_txt, (10, 98))

    # Gold + extras line
    extras = []
    total_gold = settings_module.config.get("gold", 0)
    extras.append(f"Gold: {total_gold} (+{gold_this_run})")
    if crit_pct > 0:
        extras.append(f"Crit: {crit_pct}%")
    if revivals_remaining > 0:
        extras.append(f"Revives: {revivals_remaining}")
    armor_pct = int(getattr(player_obj, 'armor', 0) * 100)
    if armor_pct > 0:
        extras.append(f"Armor: {armor_pct}%")
    xp_mult = player_obj.stats.get("xp_gain", 1.0)
    if xp_mult > 1.0:
        extras.append(f"XP: {xp_mult:.1f}x")
    extras_str = "  |  ".join(extras)
    extras_txt = _small_font().render(extras_str, True, GOLD)
    surf.blit(extras_txt, (10, 114))

    # Wave Info (top right) with neon box
    wave_box = pygame.Rect(sw - 175, 25, 165, 72)
    bg_surf = pygame.Surface((wave_box.width, wave_box.height), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 120))
    surf.blit(bg_surf, wave_box.topleft)
    pygame.draw.rect(surf, (0, 255, 255), wave_box, 1)

    wave_text = _font().render(f"Wave: {wave}", True, (0, 255, 255))
    enemy_text = _font().render(f"Enemies: {len(enemy_group)}", True, (200, 200, 255))
    surf.blit(wave_text, (sw - 165, 30))
    surf.blit(enemy_text, (sw - 165, 55))
    esc_text = _small_font().render("[ESC] Pause", True, (80, 80, 100))
    surf.blit(esc_text, (sw - 165, 80))

    draw_upgrade_counters(surf, player_obj)


def draw_boss_health_bar(surf, enemy_group):
    sw = settings_module.SCREEN_WIDTH
    sh = settings_module.SCREEN_HEIGHT
    for e in enemy_group:
        if e.is_boss:
            bar_w, bar_h = 400, 25
            bar_x = sw // 2 - bar_w // 2
            bar_y = sh - 50
            hp_ratio = max(0, e.health / e.max_health)

            _neon_bar(surf, bar_x, bar_y, bar_w, bar_h, hp_ratio, (180, 0, 255), (220, 50, 255))

            txt = _boss_font().render("BOSS", True, (220, 50, 255))
            # Glow behind boss text
            glow = pygame.Surface((txt.get_width() + 20, txt.get_height() + 10), pygame.SRCALPHA)
            glow.fill((180, 0, 255, 30))
            surf.blit(glow, (bar_x + bar_w // 2 - glow.get_width() // 2, bar_y - 40))
            surf.blit(txt, (bar_x + bar_w // 2 - txt.get_width() // 2, bar_y - 35))


def draw_wave_banner(surf, wave):
    sw = settings_module.SCREEN_WIDTH
    sh = settings_module.SCREEN_HEIGHT
    if wave % 10 == 0:
        color = (220, 50, 255)
        text = _title_font().render(f"WAVE {wave} - BOSS!", True, color)
    else:
        color = (255, 165, 0)
        text = _title_font().render(f"WAVE {wave}", True, color)

    # Neon glow behind banner
    glow = pygame.Surface((text.get_width() + 40, text.get_height() + 20), pygame.SRCALPHA)
    glow.fill((*color[:3], 25))
    surf.blit(glow, (sw // 2 - glow.get_width() // 2, sh // 2 - 110))
    surf.blit(text, (sw // 2 - text.get_width() // 2, sh // 2 - 100))


def draw_enemy_health_bars(surf, enemy_group):
    for e in enemy_group:
        e.draw_health_bar(surf)