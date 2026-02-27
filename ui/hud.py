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
    """Draw a neon-styled progress bar — no Surface allocation."""
    pygame.draw.rect(surf, (15, 15, 25), (x, y, w, h))
    fill_w = int(w * max(0, min(1, ratio)))
    if fill_w > 0:
        pygame.draw.rect(surf, bar_color, (x, y, fill_w, h))
        if fill_w > 2:
            pygame.draw.line(surf, (min(255, bar_color[0] + 80), min(255, bar_color[1] + 80), min(255, bar_color[2] + 80)),
                             (x + fill_w - 1, y + 1), (x + fill_w - 1, y + h - 2), 1)
    if glow:
        gc = (max(0, border_color[0]//10), max(0, border_color[1]//10), max(0, border_color[2]//10))
        pygame.draw.rect(surf, gc, (x - 3, y - 3, w + 6, h + 6), 2)
    pygame.draw.rect(surf, border_color, (x, y, w, h), 1)


def draw_upgrade_counters(surf, player_obj):
    s = settings_module.S
    sx_off = s(8)
    sy_off = s(155)

    # Map every upgrade key to a merged display name + color
    # big_ variants fold into their base key
    _BASE = {
        "speed": ("Speed", (100,255,200)),
        "fire_rate": ("Fire Rate", (100,200,255)),
        "bullet_speed": ("Bullet Spd", (255,180,50)),
        "max_health": ("Max HP", (255,100,120)),
        "multishot": ("Multishot", (180,150,255)),
        "damage": ("Damage", (255,80,80)),
        "piercing": ("Pierce", (0,255,255)),
        "magnet": ("Magnet", (255,215,0)),
        "bullet_size": ("Bullet Size", (200,150,255)),
        "xp_gain": ("XP Gain", (255,200,50)),
        "accuracy": ("Accuracy", (150,255,150)),
        # Class-specific (no big_ variant to merge)
        "balanced_boost": ("Balanced", (57,255,20)),
        "survival_instinct": ("Survival", (57,255,20)),
        "ram_damage": ("Ram", (120,170,220)),
        "fortress": ("Fortress", (120,170,220)),
        "beam_width": ("Beam Width", (255,80,80)),
        "beam_bounce": ("Chain", (255,100,100)),
        "bullet_storm": ("Storm", (255,165,0)),
        "explosive_rounds": ("Explosive", (255,165,0)),
        "headshot": ("Headshot", (200,80,255)),
        "long_range": ("Long Range", (200,80,255)),
        "holy_aura": ("Aura", (255,220,100)),
        "divine_shield": ("Shield", (255,220,100)),
    }
    # Map big_ keys to their base for merging
    _BIG_TO_BASE = {
        "big_speed": "speed", "big_fire_rate": "fire_rate",
        "big_bullet_speed": "bullet_speed", "big_max_health": "max_health",
        "big_multishot": "multishot", "big_damage": "damage",
        "big_piercing": "piercing", "big_magnet": "magnet",
        "big_bullet_size": "bullet_size", "big_xp_gain": "xp_gain",
        "big_accuracy": "accuracy",
        "big_balanced": "balanced_boost", "big_ram": "ram_damage",
        "big_beam": "beam_width", "big_storm": "bullet_storm",
        "big_snipe": "headshot", "big_divine": "divine_shield",
    }

    picks = getattr(player_obj, 'upgrade_picks', {})
    if not picks:
        return

    # Merge big + normal counts
    merged = {}  # base_key -> total count
    for key, count in picks.items():
        if count <= 0:
            continue
        base = _BIG_TO_BASE.get(key, key)
        merged[base] = merged.get(base, 0) + count

    if not merged:
        return

    # Header
    header = _font().render("UPGRADES", True, (0, 200, 255))
    surf.blit(header, (sx_off, sy_off))
    line_top = sy_off + header.get_height() + s(2)
    pygame.draw.line(surf, (0, 150, 200), (sx_off, line_top), (sx_off + s(140), line_top), 1)

    # Single column list
    row_h = s(18)
    start_y = line_top + s(4)
    fnt = _small_font()
    bar_w = s(150)

    # Sort by count descending
    sorted_merged = sorted(merged.items(), key=lambda kv: -kv[1])

    for i, (base_key, count) in enumerate(sorted_merged):
        info = _BASE.get(base_key, (base_key.replace("_"," ").title(), (150,150,160)))
        label, color = info

        ty = start_y + i * row_h

        # Background
        bg_surf = pygame.Surface((bar_w, row_h - s(2)), pygame.SRCALPHA)
        bg_surf.fill((10, 12, 24, 160))
        surf.blit(bg_surf, (sx_off, ty))

        # Left accent
        pygame.draw.rect(surf, color, (sx_off, ty, s(2), row_h - s(2)))

        # "Label x3" as one string so it never overlaps
        if count > 1:
            text = f"{label} x{count}"
        else:
            text = label
        lt = fnt.render(text, True, color)
        surf.blit(lt, (sx_off + s(6), ty + (row_h - s(2)) // 2 - lt.get_height() // 2))

    # Stat summary
    summary_y = start_y + len(sorted_merged) * row_h + s(4)
    stats = player_obj.stats
    summary = f"DMG {stats['damage']}  SPD {stats['speed']}  RATE {stats['fire_rate']}"
    st = fnt.render(summary, True, (80, 90, 110))
    surf.blit(st, (sx_off, summary_y))


def draw_ui(surf, player_obj, wave, enemy_group, net_mode=None, party_level=None, party_xp=None, party_xp_to_next=None,
            gold_this_run=0, revivals_remaining=0):
    global _hud_time
    _hud_time += 0.03
    sw = settings_module.SCREEN_WIDTH
    s = settings_module.S

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

    xp_bar_h = s(22)
    _neon_bar(surf, 0, 0, sw, xp_bar_h, xp_ratio, (0, 80, 200), (0, 150, 255))
    pulse_x = int(xp_ratio * sw)
    if pulse_x > 5:
        pulse_bright = int(40 + math.sin(_hud_time * 4) * 20)
        pygame.draw.rect(surf, (pulse_bright, pulse_bright + 40, pulse_bright + 60), (pulse_x - s(3), 0, s(6), xp_bar_h))

    xp_text = _font().render(f"LVL {current_level}  ({current_xp_val}/{xp_to_next})", True, (200, 230, 255))
    surf.blit(xp_text, (s(10), xp_bar_h + s(2)))

    # Health Bar with neon
    hp_bar_w, hp_bar_h = s(200), s(20)
    hp_x, hp_y = s(10), xp_bar_h + s(26)
    max_hp = max(1, player_obj.stats["max_health"])
    hp_ratio = max(0, player_obj.current_health / max_hp)

    if hp_ratio > 0.5:
        bar_col, border_col = (0, 230, 100), (57, 255, 20)
    elif hp_ratio > 0.25:
        bar_col, border_col = (255, 165, 0), (255, 200, 0)
    else:
        bar_col, border_col = (255, 30, 60), (255, 50, 80)

    _neon_bar(surf, hp_x, hp_y, hp_bar_w, hp_bar_h, hp_ratio, bar_col, border_col)
    hp_str = f"{max(0, player_obj.current_health)} / {player_obj.stats['max_health']}"
    hp_text = _font().render(hp_str, True, WHITE)
    surf.blit(hp_text, (hp_x + hp_bar_w // 2 - hp_text.get_width() // 2,
                        hp_y + hp_bar_h // 2 - hp_text.get_height() // 2))

    # Quick Stats
    quick = _font().render(
        f"DMG:{player_obj.stats['damage']}  PIERCE:{player_obj.stats['piercing']}  "
        f"MULTI:{player_obj.stats['multishot']}  MAG:{player_obj.get_magnet_radius()}px",
        True, (180, 220, 255))
    surf.blit(quick, (s(10), hp_y + hp_bar_h + s(8)))

    class_txt = _small_font().render(f"Class: {player_obj.DISPLAY_NAME}", True, player_obj.SPRITE_COLOR)
    surf.blit(class_txt, (s(10), hp_y + hp_bar_h + s(28)))

    # Gold + extras line
    extras = []
    total_gold = settings_module.config.get("gold", 0)
    extras.append(f"Gold: {total_gold} (+{gold_this_run})")
    crit_pct = int(getattr(player_obj, 'crit_chance', 0) * 100)
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
    surf.blit(extras_txt, (s(10), hp_y + hp_bar_h + s(46)))

    # Wave Info (top right) with neon box
    box_w, box_h = s(165), s(72)
    wave_box = pygame.Rect(sw - box_w - s(10), xp_bar_h + s(3), box_w, box_h)
    pygame.draw.rect(surf, (0, 0, 0), wave_box)  # Solid black bg instead of alpha surface
    pygame.draw.rect(surf, (0, 255, 255), wave_box, 1)

    wx = wave_box.x + s(10)
    wave_text = _font().render(f"Wave: {wave}", True, (0, 255, 255))
    enemy_text = _font().render(f"Enemies: {len(enemy_group)}", True, (200, 200, 255))
    surf.blit(wave_text, (wx, wave_box.y + s(5)))
    surf.blit(enemy_text, (wx, wave_box.y + s(28)))
    esc_text = _small_font().render("[ESC] Pause", True, (80, 80, 100))
    surf.blit(esc_text, (wx, wave_box.y + s(51)))

    draw_upgrade_counters(surf, player_obj)


def draw_boss_health_bar(surf, enemy_group):
    sw = settings_module.SCREEN_WIDTH
    sh = settings_module.SCREEN_HEIGHT
    s = settings_module.S
    for e in enemy_group:
        if e.is_boss:
            bar_w, bar_h = s(400), s(25)
            bar_x = sw // 2 - bar_w // 2
            bar_y = sh - s(50)
            hp_ratio = max(0, e.health / e.max_health)

            _neon_bar(surf, bar_x, bar_y, bar_w, bar_h, hp_ratio, (180, 0, 255), (220, 50, 255))

            txt = _boss_font().render("BOSS", True, (220, 50, 255))
            surf.blit(txt, (bar_x + bar_w // 2 - txt.get_width() // 2, bar_y - s(35)))


def draw_wave_banner(surf, wave):
    sw = settings_module.SCREEN_WIDTH
    sh = settings_module.SCREEN_HEIGHT
    s = settings_module.S
    if wave % 10 == 0:
        color = (220, 50, 255)
        text = _title_font().render(f"WAVE {wave} - BOSS!", True, color)
    else:
        color = (255, 165, 0)
        text = _title_font().render(f"WAVE {wave}", True, color)

    surf.blit(text, (sw // 2 - text.get_width() // 2, sh // 2 - s(100)))


def draw_enemy_health_bars(surf, enemy_group):
    for e in enemy_group:
        e.draw_health_bar(surf)


def draw_fps_ping(surf, fps, ping_ms=None):
    """Draw FPS and optional ping counter in top-right, below the wave box."""
    s = settings_module.S
    sw = settings_module.SCREEN_WIDTH

    # FPS color
    fps_int = int(fps)
    if fps_int > 50:
        fps_col = (57, 255, 20)
    elif fps_int > 30:
        fps_col = (255, 200, 50)
    else:
        fps_col = (255, 50, 50)

    lines = [f"FPS: {fps_int}"]
    colors = [fps_col]

    if ping_ms is not None:
        ping_int = int(ping_ms)
        if ping_int < 60:
            ping_col = (57, 255, 20)
        elif ping_int < 120:
            ping_col = (255, 200, 50)
        else:
            ping_col = (255, 50, 50)
        lines.append(f"Ping: {ping_int}ms")
        colors.append(ping_col)

    fnt = _small_font()
    line_h = fnt.get_height() + s(2)
    box_w = s(90)
    box_h = line_h * len(lines) + s(6)
    box_x = sw - box_w - s(10)
    box_y = s(100)  # Below wave box area

    pygame.draw.rect(surf, (0, 0, 0), (box_x, box_y, box_w, box_h))

    for i, (text, col) in enumerate(zip(lines, colors)):
        t = fnt.render(text, True, col)
        surf.blit(t, (box_x + s(5), box_y + s(3) + i * line_h))