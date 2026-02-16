# upgrade_menu.py
"""Level-up upgrade selection — big vertical stat cards."""

import pygame, sys, random, math
import core.settings as settings_module
from core.settings import *
from core.game_state import (
    display_mgr, clock, gs,
    font, small_font, title_font, menu_font, header_font, desc_font,
    MSG_UPGRADE_PAUSE, MSG_UPGRADE_RESUME
)
from ui.hud import draw_enemy_health_bars

from networking.net_common import MSG_UPGRADE_DONE

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
}

# Persistent auto-upgrade toggle (survives between level-ups)
_auto_upgrade_on = False

def _draw_upgrade_icon(surf, cx, cy, key, color, r=16):
    """Draw a small icon for upgrade type."""
    base = key.replace("big_","")
    if base == "damage":
        pygame.draw.polygon(surf, color, [(cx,cy-r),(cx+r//2,cy),(cx,cy+r//3),(cx-r//2,cy)], 2)
        pygame.draw.line(surf, color, (cx,cy-r),(cx,cy+r), 2)
    elif base == "max_health":
        pygame.draw.rect(surf, color, (cx-2,cy-r//2,5,r), border_radius=1)
        pygame.draw.rect(surf, color, (cx-r//2,cy-2,r,5), border_radius=1)
    elif base == "speed":
        pts = [(cx-r//2,cy-r//3),(cx+r//4,cy-r//3),(cx+r//4,cy-r//2),
               (cx+r//2,cy),(cx+r//4,cy+r//2),(cx+r//4,cy+r//3),(cx-r//2,cy+r//3)]
        pygame.draw.polygon(surf, color, pts, 2)
    elif base == "piercing":
        for off in [-5,0,5]:
            pygame.draw.line(surf, color, (cx+off,cy+6),(cx+off,cy-8), 2)
            pygame.draw.line(surf, color, (cx+off-3,cy-4),(cx+off,cy-8), 2)
            pygame.draw.line(surf, color, (cx+off+3,cy-4),(cx+off,cy-8), 2)
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
        pygame.draw.line(surf, color, (cx-r//3,cy),(cx-r//3,cy-r//2), 3)
        pygame.draw.line(surf, color, (cx+r//3,cy),(cx+r//3,cy-r//2), 3)
    elif base == "bullet_speed":
        pygame.draw.line(surf, color, (cx-r,cy),(cx+r,cy), 2)
        pygame.draw.line(surf, color, (cx+r//2,cy-r//3),(cx+r,cy), 2)
        pygame.draw.line(surf, color, (cx+r//2,cy+r//3),(cx+r,cy), 2)
    elif base == "xp_gain":
        pygame.draw.polygon(surf, color, [(cx,cy-r),(cx+r//2,cy+r//3),(cx-r//2,cy+r//3)], 2)
    elif base == "accuracy":
        pygame.draw.circle(surf, color, (cx,cy), r//2, 2)
        pygame.draw.circle(surf, color, (cx,cy), 2)
    else:
        pygame.draw.circle(surf, color, (cx,cy), r//2, 2)
        pygame.draw.circle(surf, color, (cx,cy), 3)

def _get_stat_value(player_obj, key):
    """Get the player's current value for a given upgrade key."""
    base = key.replace("big_","")
    s = player_obj.stats
    if base == "speed": return str(s.get("speed","?"))
    elif base == "fire_rate": return str(s.get("fire_rate","?"))
    elif base == "bullet_speed": return str(s.get("bullet_speed","?"))
    elif base == "max_health": return str(s.get("max_health","?"))
    elif base == "multishot": return str(s.get("multishot","?"))
    elif base == "damage": return str(s.get("damage","?"))
    elif base == "piercing": return str(s.get("piercing","?"))
    elif base == "magnet": return str(s.get("magnet_range","?"))
    elif base == "accuracy": return f"{s.get('accuracy',0):.1f}"
    elif base == "xp_gain": return f"{getattr(player_obj,'xp_multiplier',1.0):.0%}"
    elif base == "heal": return f"{player_obj.current_health}/{s.get('max_health','?')}"
    return "?"


def show_upgrade_menu(is_big, player_obj, all_spr, enemy_grp, net_mode=None, net_host=None, net_client=None):
    if net_mode == "host" and net_host:
        gs.upgrade_paused_by = {"player_name":"Host","level":player_obj.level}
        net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name":"Host","level":player_obj.level})
    elif net_mode == "client" and net_client:
        gs.upgrade_paused_by = {"player_name":"Client","level":player_obj.level}
        net_client.send("upgrade_choosing", {"player_id":0,"choosing":True})
    else:
        gs.upgrade_paused_by = {"player_name":"Player","level":player_obj.level}

    pool = BIG_UPGRADE_POOL if is_big else UPGRADE_POOL

    weights = []
    for item in pool:
        base_key = item["key"].replace("big_","")
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
    hues = [(0,255,255),(57,255,20),(0,180,255),(255,50,200),(255,200,50)]
    global _auto_upgrade_on
    auto_timer = 0  # counts up each frame when auto is on (120 = 2 sec at 60fps)

    while True:
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        t += 0.04
        mx, my = pygame.mouse.get_pos()

        surf.fill((3,3,12))
        all_spr.draw(surf)
        draw_enemy_health_bars(surf, enemy_grp)

        ov = pygame.Surface((sw, sh))
        ov.fill((0,0,8))
        ov.set_alpha(215)
        surf.blit(ov, (0,0))

        # Title
        tc = GOLD if is_big else (0,255,255)
        ts = "BIG UPGRADE!" if is_big else "LEVEL UP!"
        tt = header_font.render(ts, True, tc)
        pulse = math.sin(t*3)*0.3+0.7
        # Title (no glow surface)
        surf.blit(tt, (sw//2-tt.get_width()//2, 20))

        lv = small_font.render(f"Level {player_obj.level}", True, (70,80,100))
        surf.blit(lv, (sw//2-lv.get_width()//2, 54))

        # Cards — tall vertical, side by side
        num = len(options)
        card_w = min(int(sw * 0.14), (sw - 40) // num - 10)
        card_h = min(int(sh * 0.7), sh - 140)
        gap = 10
        total_w = num * card_w + (num-1) * gap
        sx = sw//2 - total_w//2
        sy = 72

        rects = []
        for i, opt in enumerate(options):
            cx = sx + i * (card_w + gap)
            cy = sy
            cr = pygame.Rect(cx, cy, card_w, card_h)
            rects.append(cr)
            hov = cr.collidepoint(mx, my)
            bc = GOLD if is_big else hues[i % len(hues)]

            # BG
            bg = pygame.Surface((card_w, card_h))
            bg.fill(bc)
            bg.set_alpha(38 if hov else 10)
            surf.blit(bg, (cx, cy))

            # Top accent
            pygame.draw.rect(surf, bc, (cx, cy, card_w, 3))

            # Glow border
            # Simple border, no glow loop
            pygame.draw.rect(surf, WHITE if hov else bc, cr, 2 if not hov else 3, border_radius=6)

            # Icon
            _draw_upgrade_icon(surf, cx+card_w//2, cy+card_h//8, opt["key"], bc, r=min(18, card_w//10))

            # Name (word-wrapped)
            ny = cy + card_h//5
            words = opt["name"].split(); lines = []; cur = ""
            for w in words:
                test = cur+" "+w if cur else w
                if menu_font.size(test)[0] < card_w-14: cur = test
                else: lines.append(cur); cur = w
            if cur: lines.append(cur)
            for j, line in enumerate(lines):
                nt = menu_font.render(line, True, WHITE if hov else bc)
                surf.blit(nt, (cx+card_w//2-nt.get_width()//2, ny+j*22))

            # Description (word-wrapped)
            dy = ny + len(lines)*22 + 4
            dwords = opt.get("desc","").split(); dlines = []; cur = ""
            for w in dwords:
                test = cur+" "+w if cur else w
                if desc_font.size(test)[0] < card_w-14: cur = test
                else: dlines.append(cur); cur = w
            if cur: dlines.append(cur)
            for j, line in enumerate(dlines):
                dt = desc_font.render(line, True, (140,150,170) if hov else (80,88,100))
                surf.blit(dt, (cx+card_w//2-dt.get_width()//2, dy+j*16))

            # ── Bottom stat section
            bsy = cy + card_h - min(75, card_h//4)
            pygame.draw.line(surf, (40,40,55), (cx+10, bsy), (cx+card_w-10, bsy), 1)

            base_key = opt["key"].replace("big_","")
            stat_info = _STAT_MAP.get(base_key, (base_key.upper()[:5], (180,180,200)))
            stat_label, stat_col = stat_info

            # Stat label
            sl = small_font.render("Current " + stat_label, True, (80,90,110))
            surf.blit(sl, (cx+card_w//2-sl.get_width()//2, bsy+4))

            # Current value (big)
            val = _get_stat_value(player_obj, opt["key"])
            vt = title_font.render(val, True, stat_col)
            surf.blit(vt, (cx+card_w//2-vt.get_width()//2, bsy+22))

            # Count badge
            count = player_obj.upgrade_counts.get(base_key, 0)
            if count > 0:
                badge = small_font.render(f"x{count}", True, bc)
                bw2 = badge.get_width()+8
                bbg = pygame.Surface((bw2,18))
                bbg.fill(bc)
                bbg.set_alpha(25)
                surf.blit(bbg, (cx+card_w-bw2-4, cy+7))
                pygame.draw.rect(surf, bc, (cx+card_w-bw2-4,cy+7,bw2,18), 1, border_radius=3)
                surf.blit(badge, (cx+card_w-bw2, cy+8))

            # Hover highlight line
            if hov:
                shy = int((math.sin(t*5)*0.5+0.5)*card_h)
                pygame.draw.line(surf, bc, (cx+2, cy+shy), (cx+card_w-2, cy+shy), 1)

        # Auto-upgrade toggle + timer
        auto_w, auto_h = 200, 34
        auto_rect = pygame.Rect(sw//2 - auto_w//2, sh - 56, auto_w, auto_h)
        auto_hov = auto_rect.collidepoint(mx, my)
        ac = (57, 255, 20) if _auto_upgrade_on else (255, 200, 50)
        ab = pygame.Surface((auto_w, auto_h))
        ab.fill(ac)
        ab.set_alpha(30 if auto_hov or _auto_upgrade_on else 10)
        surf.blit(ab, auto_rect.topleft)
        pygame.draw.rect(surf, ac if auto_hov or _auto_upgrade_on else (120, 110, 60),
                         auto_rect, 2 if auto_hov else 1, border_radius=5)
        auto_label = "AUTO: ON  [A]" if _auto_upgrade_on else "AUTO: OFF  [A]"
        at = small_font.render(auto_label, True, ac if _auto_upgrade_on else ((255,200,50) if auto_hov else (120,110,60)))
        surf.blit(at, (auto_rect.centerx - at.get_width()//2, auto_rect.centery - at.get_height()//2))

        # Timer bar when auto is on
        if _auto_upgrade_on:
            auto_timer += 1
            bar_w = auto_w - 8
            bar_ratio = min(1.0, auto_timer / 120.0)  # 120 frames = 2 sec at 60fps
            bar_y = auto_rect.bottom + 2
            pygame.draw.rect(surf, (30, 30, 40), (auto_rect.x + 4, bar_y, bar_w, 6), border_radius=3)
            if bar_ratio > 0:
                pygame.draw.rect(surf, ac, (auto_rect.x + 4, bar_y, int(bar_w * bar_ratio), 6), border_radius=3)
            # Countdown text
            secs_left = max(0, 2.0 - auto_timer / 60.0)
            ct = desc_font.render(f"{secs_left:.1f}s", True, ac)
            surf.blit(ct, (auto_rect.right + 4, bar_y - 2))

            # Auto-pick after 2 seconds
            if auto_timer >= 120:
                _pick(random.randint(0, len(options)-1)); return
        else:
            auto_timer = 0



        hint = small_font.render("Click or press 1-5  |  A = toggle auto", True, (38,40,52))
        surf.blit(hint, (sw//2-hint.get_width()//2, sh-20))

        display_mgr.present()

        def _pick(idx):
            player_obj.apply_upgrade(options[idx]["key"])
            if net_mode == "client" and net_client:
                gs.upgrade_paused_by = None
                net_client.send(MSG_UPGRADE_DONE, {})
                net_client.send("upgrade_choosing", {"player_id":0,"choosing":False})
            else:
                gs.upgrade_paused_by = None

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                # 1-5 keys
                num_keys = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4}
                if ev.key in num_keys and num_keys[ev.key] < len(options):
                    _pick(num_keys[ev.key]); return
                # A = toggle auto
                if ev.key == pygame.K_a:
                    _auto_upgrade_on = not _auto_upgrade_on
                    auto_timer = 0
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if auto_rect.collidepoint(ev.pos):
                    _auto_upgrade_on = not _auto_upgrade_on
                    auto_timer = 0
                else:
                    for i, rect in enumerate(rects):
                        if rect.collidepoint(ev.pos):
                            _pick(i); return
        clock.tick(settings_module.FPS or 0)