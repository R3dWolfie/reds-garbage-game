# upgrade_menu.py
"""Level-up upgrade selection — clean, compact stat cards matching global UI style."""

import pygame, sys, random, math
import core.settings as settings_module
from core.settings import *
import core.game_state as _gs
from core.game_state import (
    display_mgr, clock, gs,
    MSG_UPGRADE_PAUSE, MSG_UPGRADE_RESUME
)
from ui.hud import draw_enemy_health_bars

from networking.net_common import MSG_UPGRADE_DONE

# ── Global standards (match other menus) ──
ACCENT = (0, 200, 255)
BG_DARK = (5, 6, 16)
TEXT_DIM = (60, 65, 80)
TEXT_MID = (130, 140, 160)
TEXT_BRIGHT = (220, 225, 240)
BORDER = (35, 40, 60)
NEON_GREEN = (57, 255, 20)

_STAT_MAP = {
    "speed": ("SPD", (100,255,200)),
    "fire_rate": ("RATE", (100,200,255)),
    "bullet_speed": ("BSPD", (255,180,50)),
    "max_health": ("HP", (255,100,120)),
    "multishot": ("MULTI", (180,150,255)),
    "damage": ("DMG", (255,80,80)),
    "piercing": ("PIERCE", (0,255,255)),
    "magnet": ("MAG", (255,215,0)),
    "accuracy": ("ACC", (150,255,150)),
    "xp_gain": ("XP", (255,200,50)),
    "heal": ("HEAL", (100,255,150)),
    "beam_bounce": ("CHAIN", (255,80,80)),
    "beam_width": ("WIDTH", (255,80,80)),
    "revive_ally": ("REVIVE", (255,215,0)),
    # Class-specific
    "bullet_storm": ("RATE", (100,200,255)),
    "explosive_rounds": ("DMG", (255,80,80)),
    "headshot": ("DMG", (255,80,80)),
    "long_range": ("PIERCE", (0,255,255)),
    "holy_aura": ("DMG", (255,80,80)),
    "divine_shield": ("HP", (255,100,120)),
    "ram_damage": ("DMG", (255,80,80)),
    "fortress": ("HP", (255,100,120)),
    "balanced_boost": ("DMG", (255,80,80)),
    "survival_instinct": ("HP", (255,100,120)),
}

_auto_upgrade_on = False


def _do_revive(player_obj):
    """Broadcast MSG_REVIVE for the nearest dead remote player."""
    from networking.net_common import MSG_REVIVE
    if not hasattr(gs, '_was_revived'):
        gs._was_revived = set()

    # Find dead players
    dead_players = []
    px, py = player_obj.rect.centerx, player_obj.rect.centery

    # Check remote_players (ghosts with is_dead)
    for pid, ghost in getattr(gs, 'remote_players', {}).items():
        is_dead = getattr(ghost, 'is_dead', False)
        if is_dead and pid not in gs._was_revived:
            gx = getattr(ghost, 'x', 0) or (ghost.rect.centerx if hasattr(ghost, 'rect') else 0)
            gy = getattr(ghost, 'y', 0) or (ghost.rect.centery if hasattr(ghost, 'rect') else 0)
            dist = ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5
            dead_players.append((pid, dist))

    # Also check host's remote states
    if gs.net_host:
        for pid, st in gs.net_host.get_remote_states().items():
            if st.get('is_dead', False) and pid not in gs._was_revived:
                gx, gy = st.get('x', 0), st.get('y', 0)
                dist = ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5
                # Avoid duplicates
                if not any(p[0] == pid for p in dead_players):
                    dead_players.append((pid, dist))

    if not dead_players:
        return

    # Pick nearest
    dead_players.sort(key=lambda x: x[1])
    target_pid = dead_players[0][0]
    gs._was_revived.add(target_pid)

    revive_data = {
        "player_id": target_pid,
        "x": px,
        "y": py,
    }

    if gs.net_host:
        gs.net_host.broadcast(MSG_REVIVE, revive_data)
        # Also update ghost on host side directly
        if target_pid in getattr(gs, 'remote_players', {}):
            gs.remote_players[target_pid].is_dead = False
    elif gs.net_client:
        gs.net_client.send(MSG_REVIVE, revive_data)

def _draw_upgrade_icon(surf, cx, cy, key, color, r=14):
    base = key.replace("big_","")
    if base == "damage":
        pygame.draw.polygon(surf, color, [(cx,cy-r),(cx+r//2,cy),(cx,cy+r//3),(cx-r//2,cy)], 2)
        pygame.draw.line(surf, color, (cx,cy-r),(cx,cy+r), 2)
    elif base == "max_health":
        pygame.draw.rect(surf, color, (cx-2,cy-r//2,4,r), border_radius=1)
        pygame.draw.rect(surf, color, (cx-r//2,cy-2,r,4), border_radius=1)
    elif base == "speed":
        pts = [(cx-r//2,cy-r//3),(cx+r//4,cy-r//3),(cx+r//4,cy-r//2),
               (cx+r//2,cy),(cx+r//4,cy+r//2),(cx+r//4,cy+r//3),(cx-r//2,cy+r//3)]
        pygame.draw.polygon(surf, color, pts, 2)
    elif base == "piercing":
        for off in [-4,0,4]:
            pygame.draw.line(surf, color, (cx+off,cy+5),(cx+off,cy-6), 2)
            pygame.draw.line(surf, color, (cx+off-2,cy-3),(cx+off,cy-6), 1)
            pygame.draw.line(surf, color, (cx+off+2,cy-3),(cx+off,cy-6), 1)
    elif base == "fire_rate":
        pygame.draw.circle(surf, color, (cx,cy), r//2, 2)
        pygame.draw.line(surf, color, (cx,cy),(cx,cy-r//3), 2)
        pygame.draw.line(surf, color, (cx,cy),(cx+r//4,cy), 2)
    elif base == "multishot":
        for a in [-35,0,35]:
            rad = math.radians(a-90)
            px = cx+int((r-2)*math.cos(rad)); py = cy+int((r-2)*math.sin(rad))
            pygame.draw.circle(surf, color, (px,py), 3)
    elif base == "magnet":
        pygame.draw.arc(surf, color, (cx-r//3,cy-r//4,r*2//3,r//2), 0, math.pi, 3)
        pygame.draw.line(surf, color, (cx-r//3,cy),(cx-r//3,cy-r//2), 2)
        pygame.draw.line(surf, color, (cx+r//3,cy),(cx+r//3,cy-r//2), 2)
    elif base == "bullet_speed":
        pygame.draw.line(surf, color, (cx-r,cy),(cx+r,cy), 2)
        pygame.draw.line(surf, color, (cx+r//2,cy-r//3),(cx+r,cy), 2)
        pygame.draw.line(surf, color, (cx+r//2,cy+r//3),(cx+r,cy), 2)
    elif base == "xp_gain":
        pygame.draw.polygon(surf, color, [(cx,cy-r),(cx+r//2,cy+r//3),(cx-r//2,cy+r//3)], 2)
    elif base == "accuracy":
        pygame.draw.circle(surf, color, (cx,cy), r//2, 2)
        pygame.draw.circle(surf, color, (cx,cy), 2)
    elif base == "revive_ally":
        # Heart / cross combo
        pygame.draw.rect(surf, color, (cx-2,cy-r//2,4,r), border_radius=1)
        pygame.draw.rect(surf, color, (cx-r//2,cy-2,r,4), border_radius=1)
        pygame.draw.circle(surf, (255,215,0), (cx,cy-r//3), 3, 1)
    else:
        pygame.draw.circle(surf, color, (cx,cy), r//2, 2)
        pygame.draw.circle(surf, color, (cx,cy), 3)

def _get_stat_value(player_obj, key):
    base = key.replace("big_","")
    s = player_obj.stats
    if base == "speed": return str(s.get("speed","?"))
    elif base == "fire_rate" or base == "bullet_storm": return str(s.get("fire_rate","?"))
    elif base == "bullet_speed": return str(s.get("bullet_speed","?"))
    elif base == "max_health" or base in ("fortress","divine_shield","survival_instinct"):
        return str(s.get("max_health","?"))
    elif base == "multishot": return str(s.get("multishot","?"))
    elif base in ("damage","ram_damage","headshot","holy_aura","explosive_rounds","balanced_boost"):
        return str(s.get("damage","?"))
    elif base in ("piercing","long_range"): return str(s.get("piercing","?"))
    elif base == "magnet": return str(s.get("magnet_range","?"))
    elif base == "accuracy": return f"{s.get('accuracy',0):.1f}"
    elif base == "xp_gain": return f"{getattr(player_obj,'xp_multiplier',1.0):.0%}"
    elif base == "heal": return f"{player_obj.current_health}/{s.get('max_health','?')}"
    elif base == "beam_width": return f"{s.get('bullet_size',1.0):.1f}"
    elif base == "beam_bounce": return str(s.get("bullet_bounces", 0))
    return "?"


def show_upgrade_menu(is_big, player_obj, all_spr, enemy_grp, net_mode=None, net_host=None, net_client=None):
    # Dead players auto-pick random
    if getattr(player_obj, 'health', 1) <= 0 or getattr(player_obj, 'current_health', 1) <= 0:
        pool = BIG_UPGRADE_POOL if is_big else UPGRADE_POOL
        options = random.sample(list(pool), min(3, len(pool)))
        player_obj.apply_upgrade(options[0]["key"])
        return

    if net_mode == "host" and net_host:
        gs.upgrade_paused_by = {"player_name":"Host","level":player_obj.level}
        net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name":"Host","level":player_obj.level})
    elif net_mode == "client" and net_client:
        gs.upgrade_paused_by = {"player_name":"Client","level":player_obj.level}
        net_client.send("upgrade_choosing", {"player_id":0,"choosing":True})
    else:
        gs.upgrade_paused_by = {"player_name":"Player","level":player_obj.level}

    pool = BIG_UPGRADE_POOL if is_big else UPGRADE_POOL
    class_key = getattr(player_obj, 'CLASS_KEY', 'default')
    class_pool = (BIG_CLASS_UPGRADES if is_big else CLASS_UPGRADES).get(class_key, [])
    pool = list(pool) + list(class_pool)

    weapon = player_obj.get_weapon_type()
    if weapon == "beam":
        _beam_skip = ("piercing", "multishot", "bullet_size", "bullet_speed", "accuracy")
        pool = [u for u in pool if not any(sk in u["key"] for sk in _beam_skip)]

    # Remove upgrades that have hit their cap
    s = player_obj.stats
    _fire_rate_capped = s.get("fire_rate", 99) <= 3
    if _fire_rate_capped:
        # Remove all upgrades that reduce fire_rate (including bullet_storm, big_storm)
        _fire_rate_keys = {"fire_rate", "big_fire_rate", "bullet_storm", "big_storm"}
        pool = [u for u in pool if u["key"] not in _fire_rate_keys]
    if s.get("bullet_size", 1.0) >= 3.0:
        _bsize_keys = {"bullet_size", "big_bullet_size", "beam_width", "big_beam"}
        pool = [u for u in pool if u["key"] not in _bsize_keys]
    if s.get("multishot", 1) >= 10:
        # Remove all upgrades that add multishot (including bullet_storm, big_storm)
        _multi_keys = {"multishot", "big_multishot", "bullet_storm", "big_storm"}
        pool = [u for u in pool if u["key"] not in _multi_keys]

    # Revive Ally — only in multiplayer when a teammate is dead and not yet revived
    if gs.net_mode is not None and not is_big:
        _revived_set = getattr(gs, '_was_revived', set())
        _any_dead = False
        for pid, state in getattr(gs, 'remote_players', {}).items():
            if getattr(state, 'is_dead', False) or (isinstance(state, dict) and state.get('is_dead', False)):
                if pid not in _revived_set:
                    _any_dead = True
                    break
        # Also check remote_states from host
        if not _any_dead and gs.net_host:
            for pid, st in gs.net_host.get_remote_states().items():
                if st.get('is_dead', False) and pid not in _revived_set:
                    _any_dead = True
                    break
        if _any_dead:
            pool.append({"key": "revive_ally", "name": "Revive Ally", "desc": "Bring a fallen ally back at half health", "_is_revive": True})

    weights = []
    for item in pool:
        base_key = item["key"].replace("big_","")
        if item.get("_is_revive"):
            weights.append(0.3)  # Rare weight — much less likely than normal upgrades
        else:
            count = player_obj.upgrade_counts.get(base_key, 0)
            weights.append(1.0 + count * 0.6)

    options = []
    pool_copy = list(zip(pool, weights))
    for _ in range(min(5, len(pool_copy))):
        total = sum(w for _, w in pool_copy)
        r = random.uniform(0, total)
        cum = 0
        for j, (item, w) in enumerate(pool_copy):
            cum += w
            if cum >= r:
                options.append(item)
                pool_copy.pop(j)
                break

    t = 0.0
    card_colors = [ACCENT, NEON_GREEN, (0,180,255), (255,50,200), (255,200,50)]
    global _auto_upgrade_on
    auto_timer = 0
    flash_active = False
    flash_timer = 0
    flash_target = -1
    flash_highlight = 0

    while True:
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        t += 0.04
        mx, my = pygame.mouse.get_pos()

        # Background - game world underneath
        surf.fill(BG_DARK)
        all_spr.draw(surf)
        draw_enemy_health_bars(surf, enemy_grp)

        # Dark overlay with vignette feel
        ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 220))
        surf.blit(ov, (0,0))

        # Animated accent line across top
        line_y = max(10, sh // 2 - 180)
        line_col = GOLD if is_big else ACCENT
        pulse_w = int(60 + abs(math.sin(t * 2)) * 40)
        line_center = sw // 2
        pygame.draw.line(surf, (*line_col, 80) if len(line_col)==3 else line_col,
                         (line_center - pulse_w, line_y), (line_center + pulse_w, line_y), 1)

        # Title with subtle glow
        tc = GOLD if is_big else ACCENT
        ts = "BIG UPGRADE!" if is_big else "LEVEL UP!"
        tt = _gs.menu_font.render(ts, True, tc)
        title_y = line_y + 4
        # Glow behind title
        glow_s = pygame.Surface((tt.get_width()+20, tt.get_height()+10), pygame.SRCALPHA)
        glow_a = int(20 + abs(math.sin(t*3))*15)
        glow_s.fill((*tc, glow_a))
        surf.blit(glow_s, (sw//2 - glow_s.get_width()//2, title_y - 3))
        surf.blit(tt, (sw//2 - tt.get_width()//2, title_y))

        # Level badge
        lvl_text = f"Lv.{player_obj.level}"
        lvl_r = _gs.small_font.render(lvl_text, True, tc)
        lvl_x = sw//2 + tt.get_width()//2 + 8
        lvl_y = title_y + tt.get_height()//2 - lvl_r.get_height()//2
        lvl_bg = pygame.Surface((lvl_r.get_width()+10, lvl_r.get_height()+4), pygame.SRCALPHA)
        lvl_bg.fill((*tc, 25))
        surf.blit(lvl_bg, (lvl_x - 5, lvl_y - 2))
        pygame.draw.rect(surf, tc, (lvl_x - 5, lvl_y - 2, lvl_r.get_width()+10, lvl_r.get_height()+4), 1, border_radius=4)
        surf.blit(lvl_r, (lvl_x, lvl_y))

        # Subtitle
        sub_text = "Choose an upgrade" if not is_big else "Choose a powerful upgrade"
        sub_r = _gs.desc_font.render(sub_text, True, TEXT_MID)
        sub_y = title_y + tt.get_height() + 2
        surf.blit(sub_r, (sw//2 - sub_r.get_width()//2, sub_y))

        # Cards — scale to screen with better proportions
        num = len(options)
        gap = 12
        avail_w = sw - 60
        card_w = min(160, (avail_w - (num-1)*gap) // num)
        card_h = min(220, sh - 170)
        total_w = num * card_w + (num-1) * gap
        sx = sw//2 - total_w//2
        sy = sub_y + sub_r.get_height() + 12

        rects = []
        for i, opt in enumerate(options):
            cx = sx + i * (card_w + gap)
            cy = sy
            cr = pygame.Rect(cx, cy, card_w, card_h)
            rects.append(cr)
            hov = cr.collidepoint(mx, my) and not flash_active
            is_flash = flash_active and (flash_highlight % len(options) == i)
            bc = GOLD if is_big else card_colors[i % len(card_colors)]

            # Outer glow on hover/flash
            if hov or is_flash:
                glow_pad = 6
                glow_rect = pygame.Surface((card_w + glow_pad*2, card_h + glow_pad*2), pygame.SRCALPHA)
                ga = 45 if is_flash else 30
                pygame.draw.rect(glow_rect, (*bc, ga), (0, 0, card_w+glow_pad*2, card_h+glow_pad*2),
                                 border_radius=8)
                surf.blit(glow_rect, (cx - glow_pad, cy - glow_pad))

            # Card background - glass effect
            cs = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            if is_flash:
                cs.fill((255, 255, 255, 35))
            elif hov:
                # Gradient-ish fill for hover
                cs.fill((bc[0]//10, bc[1]//10, bc[2]//10, 220))
                # Top highlight
                hl = pygame.Surface((card_w, card_h//3), pygame.SRCALPHA)
                hl.fill((*bc, 12))
                cs.blit(hl, (0, 0))
            else:
                cs.fill((12, 14, 28, 210))
            surf.blit(cs, (cx, cy))

            # Top accent bar (thicker, with fade)
            accent_h = 3
            accent_s = pygame.Surface((card_w, accent_h), pygame.SRCALPHA)
            accent_s.fill((*bc, 200 if hov else 140))
            surf.blit(accent_s, (cx, cy))

            # Border
            bw = 2 if (hov or is_flash) else 1
            bcolor = (255,255,255) if is_flash else (bc if hov else (40, 45, 65))
            pygame.draw.rect(surf, bcolor, cr, bw, border_radius=6)

            # Keybind badge (top-left, cleaner)
            kbd_text = str(i+1)
            kt = _gs.desc_font.render(kbd_text, True, bc if not is_flash else (255,255,255))
            kbd_r = pygame.Rect(cx+5, cy+7, 16, 16)
            kbd_bg = pygame.Surface((16, 16), pygame.SRCALPHA)
            kbd_bg.fill((10, 12, 25, 180))
            surf.blit(kbd_bg, kbd_r.topleft)
            pygame.draw.rect(surf, bc if not is_flash else (255,255,255), kbd_r, 1, border_radius=4)
            surf.blit(kt, (kbd_r.centerx - kt.get_width()//2, kbd_r.centery - kt.get_height()//2))

            # Icon area - circle background
            icon_cy = cy + accent_h + 22
            icon_cx = cx + card_w // 2
            icon_bg = pygame.Surface((32, 32), pygame.SRCALPHA)
            ica = 35 if hov else 18
            pygame.draw.circle(icon_bg, (*bc, ica), (16, 16), 16)
            surf.blit(icon_bg, (icon_cx - 16, icon_cy - 16))
            _draw_upgrade_icon(surf, icon_cx, icon_cy, opt["key"], bc if not hov else (255,255,255))

            # Name (small_font, word-wrapped, brighter on hover)
            ny = icon_cy + 20
            words = opt["name"].split(); lines = []; cur = ""
            for w in words:
                test = cur+" "+w if cur else w
                if _gs.small_font.size(test)[0] < card_w - 14: cur = test
                else: lines.append(cur); cur = w
            if cur: lines.append(cur)
            for j, line in enumerate(lines):
                nc = (255,255,255) if hov else bc
                nt = _gs.small_font.render(line, True, nc)
                surf.blit(nt, (cx + card_w//2 - nt.get_width()//2, ny + j*16))

            # Description (desc_font, word-wrapped)
            dy = ny + len(lines)*16 + 5
            dwords = opt.get("desc","").split(); dlines = []; cur = ""
            for w in dwords:
                test = cur+" "+w if cur else w
                if _gs.desc_font.size(test)[0] < card_w - 14: cur = test
                else: dlines.append(cur); cur = w
            if cur: dlines.append(cur)
            max_desc_lines = max(1, (card_h - (dy - cy) - 56) // 13)
            for j, line in enumerate(dlines[:max_desc_lines]):
                dc = TEXT_MID if hov else TEXT_DIM
                dt = _gs.desc_font.render(line, True, dc)
                surf.blit(dt, (cx + card_w//2 - dt.get_width()//2, dy + j*13))

            # Bottom stat area - separator + stat display
            bsy = cy + card_h - 44
            # Subtle gradient separator instead of hard line
            sep_s = pygame.Surface((card_w - 16, 1), pygame.SRCALPHA)
            sep_s.fill((255, 255, 255, 20))
            surf.blit(sep_s, (cx + 8, bsy))

            base_key = opt["key"].replace("big_","")
            stat_info = _STAT_MAP.get(base_key, (base_key.upper()[:5], (180,180,200)))
            stat_label, stat_col = stat_info
            sl = _gs.desc_font.render(stat_label, True, (80, 85, 100))
            surf.blit(sl, (cx + card_w//2 - sl.get_width()//2, bsy + 4))
            val = _get_stat_value(player_obj, opt["key"])
            vt = _gs.small_font.render(val, True, stat_col if hov else (*stat_col[:3],) if len(stat_col)==3 else stat_col)
            surf.blit(vt, (cx + card_w//2 - vt.get_width()//2, bsy + 18))

            # Count badge (top-right, sleeker)
            count = player_obj.upgrade_counts.get(base_key, 0)
            if count > 0:
                badge_text = f"x{count}"
                badge = _gs.desc_font.render(badge_text, True, bc)
                bw2 = badge.get_width() + 8
                br = pygame.Rect(cx + card_w - bw2 - 4, cy + 7, bw2, 16)
                badge_bg = pygame.Surface((bw2, 16), pygame.SRCALPHA)
                badge_bg.fill((10, 12, 25, 180))
                surf.blit(badge_bg, br.topleft)
                pygame.draw.rect(surf, bc, br, 1, border_radius=4)
                surf.blit(badge, (br.centerx - badge.get_width()//2, br.centery - badge.get_height()//2))

            # Hover scan line (subtler)
            if hov:
                shy = int((math.sin(t*4)*0.5+0.5) * card_h)
                sl2 = pygame.Surface((card_w - 6, 1), pygame.SRCALPHA)
                sl2.fill((*bc, 40))
                surf.blit(sl2, (cx + 3, cy + shy))

        # Auto-upgrade toggle (cleaner design)
        auto_w, auto_h = 170, 26
        auto_rect = pygame.Rect(sw//2-auto_w//2, sy+card_h+10, auto_w, auto_h)
        auto_hov = auto_rect.collidepoint(mx, my) and not flash_active
        ac = NEON_GREEN if _auto_upgrade_on else (180, 160, 80)
        abg = pygame.Surface((auto_w, auto_h), pygame.SRCALPHA)
        abg.fill((*ac, 20 if (auto_hov or _auto_upgrade_on) else 8))
        surf.blit(abg, auto_rect.topleft)
        pygame.draw.rect(surf, ac if (auto_hov or _auto_upgrade_on) else (50, 55, 70),
                         auto_rect, 1, border_radius=5)
        _kb = settings_module.config.get("keybinds", {})
        _auto_key_code = _kb.get("auto_upgrade", pygame.K_q)
        _auto_key_name = pygame.key.name(_auto_key_code).upper()
        auto_label = f"AUTO: ON  [{_auto_key_name}]" if _auto_upgrade_on else f"AUTO: OFF  [{_auto_key_name}]"
        at = _gs.desc_font.render(auto_label, True, ac if _auto_upgrade_on else (TEXT_MID if auto_hov else TEXT_DIM))
        surf.blit(at, (auto_rect.centerx-at.get_width()//2, auto_rect.centery-at.get_height()//2))

        # Flash animation
        if flash_active:
            flash_timer += 1
            if flash_timer < 20: cs2 = 3
            elif flash_timer < 40: cs2 = 5
            elif flash_timer < 55: cs2 = 8
            else: cs2 = 12
            if flash_timer % cs2 == 0:
                flash_highlight += 1
            if flash_timer >= 70:
                flash_highlight = flash_target
            if flash_timer >= 80:
                _pick(flash_target); return
        elif _auto_upgrade_on:
            auto_timer += 1
            bar_w = auto_w - 4
            bar_ratio = min(1.0, auto_timer / 120.0)
            bar_y = auto_rect.bottom + 2
            pygame.draw.rect(surf, (30,30,40), (auto_rect.x+2, bar_y, bar_w, 3), border_radius=2)
            if bar_ratio > 0:
                pygame.draw.rect(surf, ac, (auto_rect.x+2, bar_y, int(bar_w*bar_ratio), 3), border_radius=2)
            secs = max(0, 2.0 - auto_timer/60.0)
            ct = _gs.desc_font.render(f"{secs:.1f}s", True, ac)
            surf.blit(ct, (auto_rect.right+3, bar_y-2))
            if auto_timer >= 120:
                flash_active = True; flash_timer = 0
                flash_target = random.randint(0, len(options)-1)
                flash_highlight = 0
        else:
            auto_timer = 0

        _hint_key = pygame.key.name(settings_module.config.get("keybinds", {}).get("auto_upgrade", pygame.K_q)).upper()
        hint = _gs.desc_font.render(f"Click or 1-5  |  {_hint_key} = auto", True, TEXT_DIM)
        surf.blit(hint, (sw//2-hint.get_width()//2, min(sh-12, auto_rect.bottom+12)))

        display_mgr.present()

        def _pick(idx):
            chosen = options[idx]
            if chosen.get("_is_revive"):
                _do_revive(player_obj)
            else:
                player_obj.apply_upgrade(chosen["key"])
            # Prevent accidental dash from the click that selected the upgrade
            player_obj._dash_grace = 15  # ~0.25s grace period
            if net_mode == "client" and net_client:
                gs.upgrade_paused_by = None
                net_client.send(MSG_UPGRADE_DONE, {})
                net_client.send("upgrade_choosing", {"player_id":0,"choosing":False})
            else:
                gs.upgrade_paused_by = None

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if flash_active: continue
            if ev.type == pygame.KEYDOWN:
                num_keys = {pygame.K_1:0, pygame.K_2:1, pygame.K_3:2, pygame.K_4:3, pygame.K_5:4}
                if ev.key in num_keys and num_keys[ev.key] < len(options):
                    _pick(num_keys[ev.key]); return
                _kb = settings_module.config.get("keybinds", {})
                auto_key = _kb.get("auto_upgrade", pygame.K_q)
                if ev.key == auto_key:
                    _auto_upgrade_on = not _auto_upgrade_on; auto_timer = 0
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if auto_rect.collidepoint(ev.pos):
                    _auto_upgrade_on = not _auto_upgrade_on; auto_timer = 0
                else:
                    for i, rect in enumerate(rects):
                        if rect.collidepoint(ev.pos):
                            _pick(i); return
        clock.tick(settings_module.FPS or 0)