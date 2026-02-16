# menus.py
"""Main menu, class selection, pause menu, game over — clean neon, no unicode."""

import pygame, sys, math, random
import core.settings as settings_module
from core.settings import *
from core.game_state import (
    display_mgr, clock, sounds, gs, PLAYER_CLASSES,
    header_font, title_font, menu_font, small_font, desc_font,
    GAME_NAME, VERSION
)

_t = 0.0
_hex_cache = None
_particles = []

def _build_hex_grid(sw, sh, r=55):
    grid = []
    hw, hh = int(r * math.sqrt(3)), r * 2
    for row in range(-1, sh // int(hh * 0.75) + 3):
        for col in range(-1, sw // hw + 3):
            x = col * hw + (row % 2) * (hw // 2)
            y = row * int(hh * 0.75)
            grid.append((x, y, (col * 0.4 + row * 0.6) % (2 * math.pi), r))
    return grid

def _draw_hex_bg(surf, sw, sh, t):
    global _hex_cache
    if _hex_cache is None: _hex_cache = _build_hex_grid(sw, sh)
    for hx, hy, phase, r in _hex_cache:
        p = math.sin(t * 0.7 + phase) * 0.5 + 0.5
        c = (int(p * 10), int(5 + p * 18), int(15 + p * 30))
        pts = [(hx + r * math.cos(math.radians(60 * k - 30)),
                hy + r * math.sin(math.radians(60 * k - 30))) for k in range(6)]
        pygame.draw.polygon(surf, c, pts, 1)

def _tick_particles(surf, sw, sh, t):
    global _particles
    while len(_particles) < 20:
        _particles.append([random.randint(0, sw), random.randint(0, sh),
                           random.uniform(-0.3, 0.3), random.uniform(-0.8, -0.2),
                           random.choice([(255,30,60),(0,255,255),(57,255,20),(255,215,0)]),
                           random.randint(1, 3), random.uniform(0, 6.28)])
    alive = []
    for p in _particles:
        p[0] += p[2]; p[1] += p[3]; p[6] += 0.03
        a = int((math.sin(p[6]) * 0.5 + 0.5) * 80 + 20)
        ps = pygame.Surface((p[5]*4, p[5]*4), pygame.SRCALPHA)
        pygame.draw.circle(ps, (*p[4], min(255, a)), (p[5]*2, p[5]*2), p[5])
        surf.blit(ps, (int(p[0]-p[5]*2), int(p[1]-p[5]*2)))
        if 0 <= p[0] <= sw and -50 <= p[1] <= sh + 50: alive.append(p)
    _particles = alive

def _neon_text(surf, text, fnt, color, cx, cy, pulse_t=0):
    txt = fnt.render(text, True, color)
    tx, ty = cx - txt.get_width()//2, cy - txt.get_height()//2
    if pulse_t:
        p = math.sin(pulse_t) * 0.4 + 0.6
        gs2 = pygame.Surface((txt.get_width()+20, txt.get_height()+10), pygame.SRCALPHA)
        gs2.fill((*color[:3], int(12 * p)))
        surf.blit(gs2, (tx-10, ty-5))
    surf.blit(txt, (tx, ty))

def _neon_btn(surf, rect, label, color, fnt, mx, my, t):
    """Neon button — no icons, clean text only."""
    hov = rect.collidepoint(mx, my)
    # BG
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((*color[:3], 50 if hov else 12))
    surf.blit(bg, rect.topleft)
    # Border glow
    gr = 8 if hov else 3
    for i in range(gr, 0, -2):
        a = int((20 if hov else 8) * i / gr)
        pygame.draw.rect(surf, (*color[:3], a), (rect.x-i, rect.y-i, rect.w+i*2, rect.h+i*2), 2, border_radius=6)
    pygame.draw.rect(surf, color, rect, 2 if not hov else 3, border_radius=6)
    # Text centered
    txt = fnt.render(label, True, WHITE if hov else color)
    surf.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
    return hov

def _divider(surf, cx, y, t, color=(255,30,60)):
    w = int(180 + math.sin(t * 1.5) * 40)
    pygame.draw.line(surf, color, (cx-w//2, y), (cx+w//2, y), 1)
    pygame.draw.circle(surf, color, (cx, y), 2)

def _draw_class_icon(surf, cx, cy, sz, key, color):
    """Draw a big unique shape for each class — no squares."""
    r = sz // 2
    if key == "default":
        # Survivor — bold crosshair with filled center dot
        pygame.draw.circle(surf, color, (cx, cy), r, 3)
        pygame.draw.circle(surf, color, (cx, cy), r*2//3, 2)
        pygame.draw.circle(surf, color, (cx, cy), r//3)
        pygame.draw.line(surf, color, (cx-r-4, cy), (cx-r*2//3+2, cy), 3)
        pygame.draw.line(surf, color, (cx+r*2//3-2, cy), (cx+r+4, cy), 3)
        pygame.draw.line(surf, color, (cx, cy-r-4), (cx, cy-r*2//3+2), 3)
        pygame.draw.line(surf, color, (cx, cy+r*2//3-2), (cx, cy+r+4), 3)
    elif key == "tank":
        # Juggernaut — bold shield outline with cross
        pts = [(cx, cy-r), (cx+r-4, cy-r//2), (cx+r-4, cy+r//2),
               (cx, cy+r), (cx-r+4, cy+r//2), (cx-r+4, cy-r//2)]
        pygame.draw.polygon(surf, color, pts, 4)
        pygame.draw.line(surf, color, (cx, cy-r//2), (cx, cy+r//2), 3)
        pygame.draw.line(surf, color, (cx-r//3, cy), (cx+r//3, cy), 3)
        # Inner circle
        pygame.draw.circle(surf, color, (cx, cy), r//3, 2)
    elif key == "laser":
        # Arcanist — starburst with glowing orb center
        for i in range(12):
            a = math.radians(30 * i)
            inner = r // 4
            outer = r if i % 2 == 0 else r * 2 // 3
            x1 = cx + int(inner * math.cos(a))
            y1 = cy + int(inner * math.sin(a))
            x2 = cx + int(outer * math.cos(a))
            y2 = cy + int(outer * math.sin(a))
            pygame.draw.line(surf, color, (x1, y1), (x2, y2), 2 if i % 2 else 3)
        pygame.draw.circle(surf, color, (cx, cy), r//4)
        # Glow ring
        glow = pygame.Surface((sz+8, sz+8), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color[:3], 30), (sz//2+4, sz//2+4), r//3+4)
        surf.blit(glow, (cx-sz//2-4, cy-sz//2-4))
    elif key == "gunner":
        # Gunner — triple barrel / gatling
        for off in [-r//3, 0, r//3]:
            pygame.draw.line(surf, color, (cx+off, cy+r//3), (cx+off, cy-r), 3)
            pygame.draw.circle(surf, color, (cx+off, cy-r), 3)
        # Base
        pygame.draw.rect(surf, color, (cx-r//2, cy+r//4, r, r//3), border_radius=3)
    elif key == "sniper":
        # Sniper — long rifle with scope
        pygame.draw.line(surf, color, (cx, cy+r), (cx, cy-r), 3)
        pygame.draw.circle(surf, color, (cx, cy-r//2), r//3, 2)
        pygame.draw.circle(surf, color, (cx, cy-r//2), 2)
        # Stock
        pygame.draw.line(surf, color, (cx, cy+r), (cx-r//3, cy+r+4), 3)
    elif key == "paladin":
        # Paladin — cross/plus with glow ring
        pygame.draw.rect(surf, color, (cx-r//5, cy-r+2, r*2//5, r*2-4), border_radius=2)
        pygame.draw.rect(surf, color, (cx-r+2, cy-r//5, r*2-4, r*2//5), border_radius=2)
        # Aura ring
        glow = pygame.Surface((sz+8, sz+8), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color[:3], 25), (sz//2+4, sz//2+4), r+2, 2)
        surf.blit(glow, (cx-sz//2-4, cy-sz//2-4))
    else:
        pygame.draw.circle(surf, color, (cx, cy), r, 3)
        pygame.draw.circle(surf, color, (cx, cy), r//2)


# ─── MAIN MENU ───

def show_main_menu():
    from ui.settings_menu import settings_menu
    from ui.perma_shop import show_perma_shop
    from ui.username_input import show_username_input
    from ui.hat_menu import show_hat_menu
    global _t, _hex_cache

    while True:
        _t += 0.02
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill((3, 3, 12))
        _draw_hex_bg(surf, sw, sh, _t)
        _tick_particles(surf, sw, sh, _t)

        _neon_text(surf, "Red's Garbage Game", header_font, (255,30,60), sw//2, sh//5, pulse_t=_t*2)
        _neon_text(surf, "Made With Love", desc_font, (50,50,70), sw//2, sh//5+42)

        vt = small_font.render(f"v{VERSION}", True, (35,35,50))
        surf.blit(vt, (sw - vt.get_width() - 10, sh - 20))

        bw, bh = 280, 44
        bx = sw//2 - bw//2
        gap = 50
        sy = sh//2 - 100

        gold = settings_module.config.get('gold', 0)
        btns = [
            ("PLAY",                 (57,255,20)),
            ("MULTIPLAYER",          (0,255,255)),
            (f"SHOP  ({gold}g)",     (255,200,50)),
            ("HATS",                 (255,150,200)),
            ("SETTINGS",             (160,170,190)),
            (f"NAME: {gs.local_username}", (255,100,200)),
            ("QUIT",                 (255,30,60)),
        ]
        rects = []
        for i, (lbl, col) in enumerate(btns):
            r = pygame.Rect(bx, sy + i*gap, bw, bh)
            _neon_btn(surf, r, lbl, col, menu_font, mx, my, _t)
            rects.append(r)

        hint = small_font.render("WASD move  |  SPACE/CLICK dash  |  ESC pause", True, (40,40,55))
        surf.blit(hint, (sw//2 - hint.get_width()//2, sh - 35))

        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rects[0].collidepoint(ev.pos): return "play"
                if rects[1].collidepoint(ev.pos): return "multiplayer"
                if rects[2].collidepoint(ev.pos): show_perma_shop()
                if rects[3].collidepoint(ev.pos): show_hat_menu()
                if rects[4].collidepoint(ev.pos):
                    settings_menu.run(surf.copy()); _hex_cache = None
                if rects[5].collidepoint(ev.pos): show_username_input()
                if rects[6].collidepoint(ev.pos): pygame.quit(); sys.exit()
        clock.tick(30)


# ─── CLASS SELECTION ───

def show_class_selection():
    from networking.net_host import GameHost
    from networking.net_client import GameClient
    global _t

    class_keys = list(CLASS_INFO.keys())
    waiting_for_players = False
    players_ready = set()

    # Wave skip: every 5 waves, up to (highest_wave - 5)
    highest = settings_module.config.get("highest_wave", 1)
    skip_options = [1]
    for w in range(5, highest - 4, 5):
        skip_options.append(w)
    skip_index = 0

    while True:
        _t += 0.03
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill((3, 3, 12))
        _draw_hex_bg(surf, sw, sh, _t)
        _tick_particles(surf, sw, sh, _t)

        if waiting_for_players:
            _neon_text(surf, "WAITING FOR PLAYERS...", header_font, (0,255,255), sw//2, 40, pulse_t=_t*3)
        else:
            _neon_text(surf, "CHOOSE YOUR CLASS", header_font, GOLD, sw//2, 40, pulse_t=_t*2)

        cw, ch = 220, 260
        cols = 3
        gap_x, gap_y = 16, 14
        rows = (len(class_keys) + cols - 1) // cols
        total_w = cols * cw + (cols-1) * gap_x
        total_h = rows * ch + (rows-1) * gap_y
        sx = sw//2 - total_w//2
        sy = sh//2 - total_h//2 - 20
        neon = [(57,255,20), (70,130,255), (255,60,60), (255,165,0), (200,50,255), (255,215,0)]

        card_rects = []
        for i, key in enumerate(class_keys):
            info = CLASS_INFO[key]
            row, col = i // cols, i % cols
            cx = sx + col * (cw + gap_x)
            cy = sy + row * (ch + gap_y)
            cr = pygame.Rect(cx, cy, cw, ch)
            card_rects.append((cr, key))
            hov = cr.collidepoint(mx, my)
            nc = neon[i % len(neon)]

            bg = pygame.Surface((cw, ch), pygame.SRCALPHA)
            bg.fill((*nc, 35 if hov else 10))
            pygame.draw.rect(bg, (*nc, 80 if hov else 40), (0, 0, cw, 3))
            surf.blit(bg, (cx, cy))

            gr = 6 if hov else 2
            for gi in range(gr, 0, -1):
                a = int((18 if hov else 6) * gi/gr)
                pygame.draw.rect(surf, (*nc, a), (cx-gi, cy-gi, cw+gi*2, ch+gi*2), 2, border_radius=6)
            pygame.draw.rect(surf, nc, cr, 2 if not hov else 3, border_radius=6)

            _draw_class_icon(surf, cx + cw//2, cy + 36, 48, key, nc)

            nt = menu_font.render(info["name"], True, WHITE if hov else nc)
            surf.blit(nt, (cx+cw//2-nt.get_width()//2, cy+66))

            words = info["desc"].split(); lines = []; cur = ""
            for w in words:
                test = cur+" "+w if cur else w
                if desc_font.size(test)[0] < cw-18: cur = test
                else: lines.append(cur); cur = w
            if cur: lines.append(cur)
            for j, line in enumerate(lines[:3]):
                lt = desc_font.render(line, True, (160,170,185) if not hov else (200,210,225))
                surf.blit(lt, (cx+cw//2-lt.get_width()//2, cy+88+j*14))

            cls_obj = PLAYER_CLASSES[key]; stats = cls_obj.BASE_STATS
            stat_data = [
                ("HP", stats['max_health'], (255,100,120), 200),
                ("DMG", stats['damage'], (255,200,80), 10),
                ("SPD", stats['speed'], (100,255,200), 8),
                ("RATE", stats['fire_rate'], (100,200,255), 120),
            ]
            sy_s = cy + 145
            for j, (sn, sv, sc, mx_v) in enumerate(stat_data):
                lb = small_font.render(sn, True, sc)
                vl = small_font.render(str(sv), True, (170,180,195))
                surf.blit(lb, (cx+12, sy_s+j*22))
                surf.blit(vl, (cx+cw-12-vl.get_width(), sy_s+j*22))
                bar_x = cx+48; bar_w = cw-80
                ratio = min(1.0, sv / mx_v)
                pygame.draw.rect(surf, (20,20,30), (bar_x, sy_s+j*22+4, bar_w, 7), border_radius=3)
                if ratio > 0:
                    pygame.draw.rect(surf, sc, (bar_x, sy_s+j*22+4, int(bar_w*ratio), 7), border_radius=3)

            if hov:
                sel = small_font.render("[ CLICK TO SELECT ]", True, nc)
                surf.blit(sel, (cx+cw//2-sel.get_width()//2, cy+ch-18))

        # ── Wave skip selector (always visible)
        skip_y = sy + total_h + 8
        left_r = pygame.Rect(0,0,0,0)
        right_r = pygame.Rect(0,0,0,0)
        sel_col = (0,255,255)
        cont_w = 360
        cont_x = sw//2 - cont_w//2
        cont_bg = pygame.Surface((cont_w, 36), pygame.SRCALPHA)
        cont_bg.fill((0,255,255,8))
        surf.blit(cont_bg, (cont_x, skip_y))
        pygame.draw.rect(surf, (*sel_col, 40), (cont_x, skip_y, cont_w, 36), 1, border_radius=5)

        lbl = menu_font.render("Start Wave:", True, (120,130,150))
        surf.blit(lbl, (cont_x + 12, skip_y + 7))

        if len(skip_options) > 1:
            # Left arrow
            left_r = pygame.Rect(cont_x + 150, skip_y + 4, 28, 28)
            lhov = left_r.collidepoint(mx, my)
            pygame.draw.rect(surf, sel_col if lhov else (*sel_col, 60), left_r, 0 if lhov else 1, border_radius=4)
            lt = menu_font.render("<", True, (10,10,20) if lhov else sel_col)
            surf.blit(lt, (left_r.centerx - lt.get_width()//2, left_r.centery - lt.get_height()//2))

            # Wave number
            wave_str = str(skip_options[skip_index])
            wt = menu_font.render(wave_str, True, WHITE)
            surf.blit(wt, (cont_x + 194, skip_y + 7))

            # Right arrow
            right_r = pygame.Rect(cont_x + 230, skip_y + 4, 28, 28)
            rhov = right_r.collidepoint(mx, my)
            pygame.draw.rect(surf, sel_col if rhov else (*sel_col, 60), right_r, 0 if rhov else 1, border_radius=4)
            rt = menu_font.render(">", True, (10,10,20) if rhov else sel_col)
            surf.blit(rt, (right_r.centerx - rt.get_width()//2, right_r.centery - rt.get_height()//2))
        else:
            # Only wave 1 available
            wt = menu_font.render("1", True, WHITE)
            surf.blit(wt, (cont_x + 194, skip_y + 7))

        # Best wave label
        best_lbl = small_font.render(f"Best: Wave {highest}", True, (55,60,75))
        surf.blit(best_lbl, (cont_x + cont_w - best_lbl.get_width() - 10, skip_y + 9))

        hint = small_font.render("Pick a class to begin", True, (50,50,65))
        surf.blit(hint, (sw//2-hint.get_width()//2, sh-24))

        pygame.display.flip()

        # Net
        if gs.net_mode == "host" and gs.net_host and waiting_for_players:
            for msg in gs.net_host.get_messages():
                if msg.get("type") == "class_ready": players_ready.add(msg.get("player_id",-1))
            cc = len(gs.net_host.clients) if hasattr(gs.net_host,'clients') else 0
            if len(players_ready) >= cc:
                gs.net_host.broadcast("all_classes_ready", {}); return (waiting_for_players, skip_options[skip_index])
        elif gs.net_mode == "client" and gs.net_client and waiting_for_players:
            for msg in gs.net_client.get_messages():
                if msg.get("type") == "all_classes_ready": return (waiting_for_players, skip_options[skip_index])

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and not waiting_for_players:
                if left_r.collidepoint(ev.pos):
                    skip_index = (skip_index - 1) % len(skip_options)
                elif right_r.collidepoint(ev.pos):
                    skip_index = (skip_index + 1) % len(skip_options)
                else:
                    for cr, key in card_rects:
                        if cr.collidepoint(ev.pos):
                            if gs.net_mode in ("host","client"):
                                waiting_for_players = key
                                if gs.net_mode == "host": players_ready = set()
                                elif gs.net_mode == "client": gs.net_client.send("class_ready",{"class":key})
                            else: return (key, skip_options[skip_index])
        clock.tick(30)

def show_pause_menu():
    from ui.settings_menu import settings_menu
    global _t

    while True:
        _t += 0.03
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ov.fill((0, 0, 8, 210))
        surf.blit(ov, (0, 0))

        pw, ph = 340, 310
        px, py = sw//2-pw//2, sh//2-ph//2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8, 8, 20, 230))
        surf.blit(panel, (px, py))
        pygame.draw.rect(surf, (0,255,255), (px, py, pw, ph), 2, border_radius=8)

        _neon_text(surf, "PAUSED", title_font, (0,255,255), sw//2, py+35, pulse_t=_t*2)

        btns_data = [
            ("Resume",    (57,255,20)),
            ("Settings",  (255,215,0)),
            ("Main Menu", (255,165,0)),
            ("Quit Game", (255,30,60)),
        ]
        bw, bh = 250, 42
        bx = sw//2-bw//2
        by = py + 78
        rects = []
        for i, (lbl, col) in enumerate(btns_data):
            r = pygame.Rect(bx, by+i*52, bw, bh)
            _neon_btn(surf, r, lbl, col, menu_font, mx, my, _t)
            rects.append((r, lbl.lower().replace(" ","_")))

        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return "resume"
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for r, act in rects:
                    if r.collidepoint(ev.pos):
                        if act == "settings": settings_menu.run(surf.copy())
                        elif act == "quit_game": pygame.quit(); sys.exit()
                        else: return act
        clock.tick(30)


# ─── GAME OVER ───

def show_game_over(player_obj, wave):
    global _t
    while True:
        _t += 0.03
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill((3, 3, 12))
        _draw_hex_bg(surf, sw, sh, _t)
        _tick_particles(surf, sw, sh, _t)

        p = math.sin(_t*2)*0.3+0.7
        gc = (int(255*p), int(30*p), int(60*p))
        _neon_text(surf, "GAME OVER", header_font, gc, sw//2, sh//5, pulse_t=_t*2)

        pw, ph = 400, 210
        px, py = sw//2-pw//2, sh//5+45
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8,8,20,180))
        surf.blit(panel, (px, py))
        pygame.draw.rect(surf, (255,30,60,70), (px, py, pw, ph), 1, border_radius=6)

        cn = player_obj.DISPLAY_NAME
        tg = settings_module.config.get("gold", 0)
        stats = [
            ("Class", cn, (255,200,100)),
            ("Wave Reached", str(wave), (0,255,255)),
            ("Level", str(player_obj.level), (57,255,20)),
            ("Damage", str(player_obj.stats['damage']), (255,100,100)),
            ("Pierce / Multi", f"{player_obj.stats['piercing']} / {player_obj.stats['multishot']}", (180,150,255)),
            ("Total Gold", f"{tg}g", (255,215,0)),
        ]
        for i, (lbl, val, col) in enumerate(stats):
            lt = small_font.render(lbl, True, (110,120,140))
            vt = small_font.render(val, True, col)
            surf.blit(lt, (px+18, py+12+i*30))
            surf.blit(vt, (px+pw-18-vt.get_width(), py+12+i*30))

        btns = [("Retry",(57,255,20),"restart"),("Main Menu",(255,165,0),"main_menu"),("Quit",(255,30,60),"exit")]
        bw2, bh2 = 180, 42
        total_bw = len(btns)*bw2 + (len(btns)-1)*15
        bsx = sw//2 - total_bw//2
        by = py + ph + 25
        rects = []
        for i, (lbl, col, act) in enumerate(btns):
            r = pygame.Rect(bsx+i*(bw2+15), by, bw2, bh2)
            _neon_btn(surf, r, lbl, col, menu_font, mx, my, _t)
            rects.append((r, act))

        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for r, act in rects:
                    if r.collidepoint(ev.pos):
                        if act == "exit": pygame.quit(); sys.exit()
                        return act
        clock.tick(30)