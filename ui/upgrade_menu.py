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
}

_auto_upgrade_on = False

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
    else:
        pygame.draw.circle(surf, color, (cx,cy), r//2, 2)
        pygame.draw.circle(surf, color, (cx,cy), 3)

def _get_stat_value(player_obj, key):
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
        pool = [u for u in pool if "piercing" not in u["key"] and "multishot" not in u["key"]]

    # Remove upgrades that have hit their cap
    s = player_obj.stats
    if s.get("fire_rate", 99) <= 2:
        pool = [u for u in pool if "fire_rate" not in u["key"]]
    if s.get("bullet_size", 1.0) >= 3.0:
        pool = [u for u in pool if "bullet_size" not in u["key"]]
    if s.get("multishot", 1) >= 10:
        pool = [u for u in pool if "multishot" not in u["key"]]

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

        # Background
        surf.fill(BG_DARK)
        all_spr.draw(surf)
        draw_enemy_health_bars(surf, enemy_grp)
        ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 210))
        surf.blit(ov, (0,0))

        # Title — menu_font, matches other menus
        tc = GOLD if is_big else ACCENT
        ts = "BIG UPGRADE!" if is_big else "LEVEL UP!"
        tt = _gs.menu_font.render(ts, True, tc)
        title_y = max(16, sh // 2 - 165)
        surf.blit(tt, (sw//2 - tt.get_width()//2, title_y))

        # Cards — scale to screen
        num = len(options)
        gap = 8
        avail_w = sw - 50
        card_w = min(150, (avail_w - (num-1)*gap) // num)
        card_h = min(210, sh - 150)
        total_w = num * card_w + (num-1) * gap
        sx = sw//2 - total_w//2
        sy = title_y + tt.get_height() + 10

        rects = []
        for i, opt in enumerate(options):
            cx = sx + i * (card_w + gap)
            cy = sy
            cr = pygame.Rect(cx, cy, card_w, card_h)
            rects.append(cr)
            hov = cr.collidepoint(mx, my) and not flash_active
            is_flash = flash_active and (flash_highlight % len(options) == i)
            bc = GOLD if is_big else card_colors[i % len(card_colors)]

            # Card bg
            cs = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            if is_flash:
                cs.fill((255, 255, 255, 40))
            elif hov:
                cs.fill((*bc, 28))
            else:
                cs.fill((15, 17, 30, 200))
            surf.blit(cs, (cx, cy))

            # Top accent
            pygame.draw.rect(surf, bc, (cx, cy, card_w, 2))
            # Border
            bw = 2 if (hov or is_flash) else 1
            bcolor = (255,255,255) if is_flash else (bc if hov else BORDER)
            pygame.draw.rect(surf, bcolor, cr, bw, border_radius=5)

            # Keybind badge
            kt = _gs.desc_font.render(str(i+1), True, bc if not is_flash else (255,255,255))
            kbd_r = pygame.Rect(cx+4, cy+4, 14, 14)
            pygame.draw.rect(surf, (20,24,40), kbd_r, 0, border_radius=3)
            pygame.draw.rect(surf, bc if not is_flash else (255,255,255), kbd_r, 1, border_radius=3)
            surf.blit(kt, (kbd_r.centerx - kt.get_width()//2, kbd_r.centery - kt.get_height()//2))

            # Icon
            icon_y = cy + 26
            _draw_upgrade_icon(surf, cx + card_w//2, icon_y, opt["key"], bc)

            # Name (small_font, word-wrapped)
            ny = icon_y + 16
            words = opt["name"].split(); lines = []; cur = ""
            for w in words:
                test = cur+" "+w if cur else w
                if _gs.small_font.size(test)[0] < card_w-10: cur = test
                else: lines.append(cur); cur = w
            if cur: lines.append(cur)
            for j, line in enumerate(lines):
                nt = _gs.small_font.render(line, True, (255,255,255) if hov else bc)
                surf.blit(nt, (cx+card_w//2-nt.get_width()//2, ny+j*16))

            # Description (desc_font, word-wrapped)
            dy = ny + len(lines)*16 + 3
            dwords = opt.get("desc","").split(); dlines = []; cur = ""
            for w in dwords:
                test = cur+" "+w if cur else w
                if _gs.desc_font.size(test)[0] < card_w-10: cur = test
                else: dlines.append(cur); cur = w
            if cur: dlines.append(cur)
            max_desc_lines = max(1, (card_h - (dy - cy) - 52) // 13)
            for j, line in enumerate(dlines[:max_desc_lines]):
                dt = _gs.desc_font.render(line, True, TEXT_MID if hov else TEXT_DIM)
                surf.blit(dt, (cx+card_w//2-dt.get_width()//2, dy+j*13))

            # Bottom stat
            bsy = cy + card_h - 42
            pygame.draw.line(surf, BORDER, (cx+6, bsy), (cx+card_w-6, bsy), 1)
            base_key = opt["key"].replace("big_","")
            stat_info = _STAT_MAP.get(base_key, (base_key.upper()[:5], (180,180,200)))
            stat_label, stat_col = stat_info
            sl = _gs.desc_font.render(stat_label, True, TEXT_DIM)
            surf.blit(sl, (cx+card_w//2-sl.get_width()//2, bsy+3))
            val = _get_stat_value(player_obj, opt["key"])
            vt = _gs.small_font.render(val, True, stat_col)
            surf.blit(vt, (cx+card_w//2-vt.get_width()//2, bsy+17))

            # Count badge
            count = player_obj.upgrade_counts.get(base_key, 0)
            if count > 0:
                badge = _gs.desc_font.render(f"x{count}", True, bc)
                bw2 = badge.get_width()+6
                br = pygame.Rect(cx+card_w-bw2-3, cy+4, bw2, 14)
                pygame.draw.rect(surf, (20,24,40), br, 0, border_radius=3)
                pygame.draw.rect(surf, bc, br, 1, border_radius=3)
                surf.blit(badge, (br.centerx-badge.get_width()//2, br.centery-badge.get_height()//2))

            # Hover scan line
            if hov:
                shy = int((math.sin(t*5)*0.5+0.5)*card_h)
                sl2 = pygame.Surface((card_w-4, 1), pygame.SRCALPHA)
                sl2.fill((*bc, 60))
                surf.blit(sl2, (cx+2, cy+shy))

        # Auto-upgrade toggle
        auto_w, auto_h = 160, 24
        auto_rect = pygame.Rect(sw//2-auto_w//2, sy+card_h+8, auto_w, auto_h)
        auto_hov = auto_rect.collidepoint(mx, my) and not flash_active
        ac = NEON_GREEN if _auto_upgrade_on else (255, 200, 50)
        abg = pygame.Surface((auto_w, auto_h), pygame.SRCALPHA)
        abg.fill((*ac, 18 if (auto_hov or _auto_upgrade_on) else 6))
        surf.blit(abg, auto_rect.topleft)
        pygame.draw.rect(surf, ac if (auto_hov or _auto_upgrade_on) else TEXT_DIM,
                         auto_rect, 1, border_radius=4)
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
            player_obj.apply_upgrade(options[idx]["key"])
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