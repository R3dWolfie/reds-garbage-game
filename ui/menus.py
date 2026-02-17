# menus.py
"""Main menu, class selection, pause menu, game over — clean modern UI."""

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
_hex_cache_size = (0, 0)
_hex_surf = None
_particles = []

# ── Shared colors ──
ACCENT = (0, 200, 255)
BG_DARK = (5, 6, 16)
PANEL_BG = (10, 12, 24)
TEXT_DIM = (60, 65, 80)
TEXT_MID = (130, 140, 160)
TEXT_BRIGHT = (220, 225, 240)


def _build_hex_grid(sw, sh, r=55):
    grid = []
    hw, hh = int(r * math.sqrt(3)), r * 2
    hex_offsets = [(r * math.cos(math.radians(60 * k - 30)),
                    r * math.sin(math.radians(60 * k - 30))) for k in range(6)]
    for row in range(-1, sh // int(hh * 0.75) + 3):
        for col in range(-1, sw // hw + 3):
            x = col * hw + (row % 2) * (hw // 2)
            y = row * int(hh * 0.75)
            pts = [(x + ox, y + oy) for ox, oy in hex_offsets]
            phase = (col * 0.4 + row * 0.6) % (2 * math.pi)
            grid.append((pts, phase))
    return grid


def _draw_hex_bg(surf, sw, sh):
    global _hex_cache, _hex_cache_size, _hex_surf
    if _hex_cache is None or _hex_cache_size != (sw, sh):
        _hex_cache = _build_hex_grid(sw, sh)
        _hex_cache_size = (sw, sh)
        # Pre-render hex grid to a surface once
        _hex_surf = pygame.Surface((sw, sh))
        _hex_surf.fill(BG_DARK)
        for pts, phase in _hex_cache:
            pygame.draw.polygon(_hex_surf, (8, 14, 28), pts, 1)
    surf.blit(_hex_surf, (0, 0))


def _tick_particles(surf, sw, sh, t):
    global _particles
    while len(_particles) < 35:
        # Varied colors: cyan, magenta, green, gold, soft blue, pink
        color_pool = [
            (0, 160, 220),    # cyan
            (180, 60, 200),   # magenta
            (50, 200, 100),   # green
            (220, 180, 50),   # gold
            (80, 120, 220),   # blue
            (220, 80, 120),   # pink
            (100, 220, 200),  # teal
        ]
        c = random.choice(color_pool)
        _particles.append([
            random.randint(0, sw), random.randint(0, sh),
            random.uniform(-1.0, 1.0), random.uniform(-2.5, -0.5),
            c,
            random.uniform(1, 4), random.uniform(0, 6.28)
        ])
    alive = []
    for p in _particles:
        p[0] += p[2]; p[1] += p[3]
        sz = max(1, int(p[5]))
        pygame.draw.circle(surf, p[4], (int(p[0]), int(p[1])), sz)
        if 0 <= p[0] <= sw and -50 <= p[1] <= sh + 50:
            alive.append(p)
    _particles = alive


def _draw_text(surf, text, fnt, color, cx, cy):
    txt = fnt.render(text, True, color)
    surf.blit(txt, (cx - txt.get_width()//2, cy - txt.get_height()//2))


def _menu_btn(surf, rect, label, fnt, mx, my, selected=False):
    hov = rect.collidepoint(mx, my)
    # Grey semi-transparent background for all states
    bg = pygame.Surface((rect.w, rect.h))
    if hov or selected:
        bg.fill((40, 45, 65))
        bg.set_alpha(140)
        surf.blit(bg, rect.topleft)
        pygame.draw.rect(surf, ACCENT, rect, 2, border_radius=6)
        txt = fnt.render(label, True, TEXT_BRIGHT)
    else:
        bg.fill((25, 28, 42))
        bg.set_alpha(128)
        surf.blit(bg, rect.topleft)
        pygame.draw.rect(surf, (40, 45, 65), rect, 1, border_radius=6)
        txt = fnt.render(label, True, TEXT_MID)
    surf.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
    return hov


def _back_btn(surf, mx, my, fnt):
    r = pygame.Rect(16, 16, 90, 34)
    hov = r.collidepoint(mx, my)
    c = ACCENT if hov else TEXT_DIM
    pygame.draw.rect(surf, c, r, 1, border_radius=5)
    t = fnt.render("< Back", True, TEXT_BRIGHT if hov else TEXT_MID)
    surf.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))
    return r, hov


def _draw_class_icon(surf, cx, cy, sz, key, color):
    r = sz // 2
    if key == "default":
        pygame.draw.circle(surf, color, (cx, cy), r, 3)
        pygame.draw.circle(surf, color, (cx, cy), r*2//3, 2)
        pygame.draw.circle(surf, color, (cx, cy), r//3)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            pygame.draw.line(surf, color, (cx+dx*(r*2//3-2), cy+dy*(r*2//3-2)), (cx+dx*(r+4), cy+dy*(r+4)), 3)
    elif key == "tank":
        pts = [(cx, cy-r), (cx+r-4, cy-r//2), (cx+r-4, cy+r//2),
               (cx, cy+r), (cx-r+4, cy+r//2), (cx-r+4, cy-r//2)]
        pygame.draw.polygon(surf, color, pts, 4)
        pygame.draw.line(surf, color, (cx, cy-r//2), (cx, cy+r//2), 3)
        pygame.draw.line(surf, color, (cx-r//3, cy), (cx+r//3, cy), 3)
        pygame.draw.circle(surf, color, (cx, cy), r//3, 2)
    elif key == "laser":
        for i in range(12):
            a = math.radians(30 * i)
            inner, outer = r // 4, r if i % 2 == 0 else r * 2 // 3
            x1, y1 = cx + int(inner * math.cos(a)), cy + int(inner * math.sin(a))
            x2, y2 = cx + int(outer * math.cos(a)), cy + int(outer * math.sin(a))
            pygame.draw.line(surf, color, (x1, y1), (x2, y2), 2 if i % 2 else 3)
        pygame.draw.circle(surf, color, (cx, cy), r//4)
    elif key == "gunner":
        for off in [-r//3, 0, r//3]:
            pygame.draw.line(surf, color, (cx+off, cy+r//3), (cx+off, cy-r), 3)
            pygame.draw.circle(surf, color, (cx+off, cy-r), 3)
        pygame.draw.rect(surf, color, (cx-r//2, cy+r//4, r, r//3), border_radius=3)
    elif key == "sniper":
        pygame.draw.line(surf, color, (cx, cy+r), (cx, cy-r), 3)
        pygame.draw.circle(surf, color, (cx, cy-r//2), r//3, 2)
        pygame.draw.circle(surf, color, (cx, cy-r//2), 2)
        pygame.draw.line(surf, color, (cx, cy+r), (cx-r//3, cy+r+4), 3)
    elif key == "paladin":
        pygame.draw.rect(surf, color, (cx-r//5, cy-r+2, r*2//5, r*2-4), border_radius=2)
        pygame.draw.rect(surf, color, (cx-r+2, cy-r//5, r*2-4, r*2//5), border_radius=2)
    else:
        pygame.draw.circle(surf, color, (cx, cy), r, 3)
        pygame.draw.circle(surf, color, (cx, cy), r//2)


# ─── MAIN MENU ───

def show_main_menu():
    from ui.settings_menu import settings_menu
    global _t, _hex_cache

    while True:
        _t += 0.02
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)
        _draw_hex_bg(surf, sw, sh)
        _tick_particles(surf, sw, sh, _t)

        _draw_text(surf, "Red's Garbage Game", header_font, (255, 40, 70), sw//2, sh//5)
        _draw_text(surf, "Made With Love", desc_font, TEXT_DIM, sw//2, sh//5 + 38)

        vt = small_font.render(f"v{VERSION}", True, (30, 30, 45))
        surf.blit(vt, (sw - vt.get_width() - 10, sh - 20))

        bw, bh = 300, 46
        bx = sw//2 - bw//2
        gap = 56
        sy = sh//2 - 80

        btns = ["Play", "Shop & Cosmetics", "Settings", "Quit"]
        rects = []
        for i, lbl in enumerate(btns):
            r = pygame.Rect(bx, sy + i * gap, bw, bh)
            _menu_btn(surf, r, lbl, menu_font, mx, my)
            rects.append(r)

        hint = small_font.render("WASD move  |  SPACE/CLICK dash  |  ESC pause", True, (30, 35, 50))
        surf.blit(hint, (sw//2 - hint.get_width()//2, sh - 35))

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rects[0].collidepoint(ev.pos): return "play"
                if rects[1].collidepoint(ev.pos): show_shop_menu()
                if rects[2].collidepoint(ev.pos):
                    settings_menu.run(surf.copy()); _hex_cache = None
                if rects[3].collidepoint(ev.pos): pygame.quit(); sys.exit()
        clock.tick(settings_module.FPS or 0)


# ─── CLASS SELECTION ───

def show_class_selection():
    from networking.net_host import GameHost
    from networking.net_client import GameClient
    global _t

    class_keys = list(CLASS_INFO.keys())
    waiting_for_players = False
    players_ready = set()

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

        surf.fill(BG_DARK)
        _draw_hex_bg(surf, sw, sh)
        _tick_particles(surf, sw, sh, _t)

        back_r, _ = _back_btn(surf, mx, my, small_font)

        if waiting_for_players:
            _draw_text(surf, "WAITING FOR PLAYERS...", header_font, ACCENT, sw//2, 40)
        else:
            _draw_text(surf, "CHOOSE YOUR CLASS", header_font, TEXT_BRIGHT, sw//2, 40)

        cw, ch = 200, 195
        cols = 3
        gap_x, gap_y = 14, 12
        rows = (len(class_keys) + cols - 1) // cols
        total_w = cols * cw + (cols-1) * gap_x
        total_h = rows * ch + (rows-1) * gap_y
        sx = sw//2 - total_w//2
        sy = sh//2 - total_h//2 - 10

        card_rects = []
        for i, key in enumerate(class_keys):
            info = CLASS_INFO[key]
            nc = info.get("color", ACCENT)
            row, col = i // cols, i % cols
            cx = sx + col * (cw + gap_x)
            cy = sy + row * (ch + gap_y)
            cr = pygame.Rect(cx, cy, cw, ch)
            card_rects.append((cr, key))
            hov = cr.collidepoint(mx, my)

            # Card bg — filled rect, no Surface allocation
            if hov:
                pygame.draw.rect(surf, (18, 24, 42), cr, 0, border_radius=8)
                pygame.draw.rect(surf, nc, cr, 2, border_radius=8)
            else:
                pygame.draw.rect(surf, (10, 12, 24), cr, 0, border_radius=8)
                pygame.draw.rect(surf, (30, 35, 55), cr, 1, border_radius=8)

            # Top accent
            pygame.draw.rect(surf, nc, (cx, cy, cw, 3), border_radius=2)

            # Icon
            _draw_class_icon(surf, cx + cw//2, cy + 46, 52, key, nc)

            # Name
            nt = menu_font.render(info["name"], True, TEXT_BRIGHT if hov else nc)
            surf.blit(nt, (cx + cw//2 - nt.get_width()//2, cy + 82))

            # Description (wrapped)
            words = info["desc"].split(); lines = []; cur = ""
            for w in words:
                test = cur + " " + w if cur else w
                if desc_font.size(test)[0] < cw - 20: cur = test
                else: lines.append(cur); cur = w
            if cur: lines.append(cur)
            for j, line in enumerate(lines[:3]):
                lt = desc_font.render(line, True, TEXT_MID if hov else TEXT_DIM)
                surf.blit(lt, (cx + cw//2 - lt.get_width()//2, cy + 105 + j * 15))

            # Stats (text only, no bars)
            cls_obj = PLAYER_CLASSES[key]; stats = cls_obj.BASE_STATS
            stat_str = f"HP:{stats['max_health']}  DMG:{stats['damage']}  SPD:{stats['speed']}"
            st = small_font.render(stat_str, True, TEXT_DIM)
            surf.blit(st, (cx + cw//2 - st.get_width()//2, cy + ch - 22))

        # Wave skip
        skip_y = sy + total_h + 12
        left_r = right_r = pygame.Rect(0,0,0,0)
        cont_x = sw//2 - 160
        lbl = menu_font.render("Start Wave:", True, TEXT_MID)
        surf.blit(lbl, (cont_x, skip_y + 5))
        if len(skip_options) > 1:
            left_r = pygame.Rect(cont_x + 140, skip_y + 2, 30, 30)
            _menu_btn(surf, left_r, "<", menu_font, mx, my)
            wt = menu_font.render(str(skip_options[skip_index]), True, TEXT_BRIGHT)
            surf.blit(wt, (cont_x + 185, skip_y + 5))
            right_r = pygame.Rect(cont_x + 220, skip_y + 2, 30, 30)
            _menu_btn(surf, right_r, ">", menu_font, mx, my)
        else:
            wt = menu_font.render("1", True, TEXT_BRIGHT)
            surf.blit(wt, (cont_x + 185, skip_y + 5))

        best_lbl = small_font.render(f"Best: Wave {highest}", True, TEXT_DIM)
        surf.blit(best_lbl, (cont_x + 280, skip_y + 9))

        display_mgr.present()

        if gs.net_mode == "host" and gs.net_host and waiting_for_players:
            for msg in gs.net_host.get_messages():
                mtype = msg.get("type", "")
                mdata = msg.get("data", {})
                if mtype == "class_ready":
                    pid = mdata.get("player_id", msg.get("_from", -1))
                    if pid != -1:
                        players_ready.add(pid)
            cc = len(gs.net_host.clients) if hasattr(gs.net_host,'clients') else 0
            if len(players_ready) >= cc:
                gs.net_host.broadcast("all_classes_ready", {}); return (waiting_for_players, skip_options[skip_index])
        elif gs.net_mode == "client" and gs.net_client and waiting_for_players:
            for msg in gs.net_client.get_messages():
                mtype = msg.get("type", "")
                if mtype == "all_classes_ready": return (waiting_for_players, skip_options[skip_index])

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return ("back", 0)
            if ev.type == pygame.MOUSEBUTTONDOWN and not waiting_for_players:
                if back_r.collidepoint(ev.pos): return ("back", 0)
                if left_r.collidepoint(ev.pos): skip_index = (skip_index - 1) % len(skip_options)
                elif right_r.collidepoint(ev.pos): skip_index = (skip_index + 1) % len(skip_options)
                else:
                    for cr, key in card_rects:
                        if cr.collidepoint(ev.pos):
                            if gs.net_mode in ("host","client"):
                                waiting_for_players = key
                                if gs.net_mode == "host": players_ready = set()
                                elif gs.net_mode == "client": gs.net_client.send("class_ready",{"class":key})
                            else: return (key, skip_options[skip_index])
        clock.tick(settings_module.FPS or 0)


def show_pause_menu():
    from ui.settings_menu import settings_menu
    global _t

    while True:
        _t += 0.03
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        ov = pygame.Surface((sw, sh))
        ov.fill((0, 0, 8))
        ov.set_alpha(210)
        surf.blit(ov, (0, 0))

        pw, ph = 320, 280
        px, py = sw//2 - pw//2, sh//2 - ph//2
        panel = pygame.Surface((pw, ph))
        panel.fill(PANEL_BG)
        panel.set_alpha(240)
        surf.blit(panel, (px, py))
        pygame.draw.rect(surf, (40, 45, 65), (px, py, pw, ph), 1, border_radius=8)

        _draw_text(surf, "PAUSED", title_font, ACCENT, sw//2, py + 35)

        btns_data = ["Resume", "Settings", "Main Menu", "Quit Game"]
        bw, bh = 240, 40
        bx = sw//2 - bw//2
        by = py + 72
        rects = []
        for i, lbl in enumerate(btns_data):
            r = pygame.Rect(bx, by + i * 48, bw, bh)
            _menu_btn(surf, r, lbl, menu_font, mx, my)
            rects.append((r, lbl.lower().replace(" ", "_")))

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return "resume"
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for r, act in rects:
                    if r.collidepoint(ev.pos):
                        if act == "settings": settings_menu.run(surf.copy())
                        elif act == "quit_game": pygame.quit(); sys.exit()
                        else: return act
        clock.tick(settings_module.FPS or 0)


def show_game_over(player_obj, wave):
    global _t
    while True:
        _t += 0.03
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)
        _draw_hex_bg(surf, sw, sh)
        _tick_particles(surf, sw, sh, _t)

        _draw_text(surf, "GAME OVER", header_font, (255, 50, 70), sw//2, sh//5)

        pw, ph = 400, 210
        px, py = sw//2 - pw//2, sh//5 + 40
        panel = pygame.Surface((pw, ph))
        panel.fill(PANEL_BG)
        panel.set_alpha(200)
        surf.blit(panel, (px, py))
        pygame.draw.rect(surf, (40, 45, 65), (px, py, pw, ph), 1, border_radius=6)

        cn = player_obj.DISPLAY_NAME
        tg = settings_module.config.get("gold", 0)
        stats = [
            ("Class", cn, ACCENT),
            ("Wave Reached", str(wave), (0, 255, 255)),
            ("Level", str(player_obj.level), (57, 255, 20)),
            ("Damage", str(player_obj.stats['damage']), (255, 100, 100)),
            ("Pierce / Multi", f"{player_obj.stats['piercing']} / {player_obj.stats['multishot']}", (180, 150, 255)),
            ("Total Gold", f"{tg}g", (255, 215, 0)),
        ]
        for i, (lbl, val, col) in enumerate(stats):
            lt = small_font.render(lbl, True, TEXT_MID)
            vt = small_font.render(val, True, col)
            surf.blit(lt, (px + 18, py + 12 + i * 30))
            surf.blit(vt, (px + pw - 18 - vt.get_width(), py + 12 + i * 30))

        btns = [("Retry", "restart"), ("Main Menu", "main_menu"), ("Quit", "exit")]
        bw2, bh2 = 160, 40
        total_bw = len(btns) * bw2 + (len(btns)-1) * 15
        bsx = sw//2 - total_bw//2
        by = py + ph + 20
        rects = []
        for i, (lbl, act) in enumerate(btns):
            r = pygame.Rect(bsx + i * (bw2 + 15), by, bw2, bh2)
            _menu_btn(surf, r, lbl, menu_font, mx, my)
            rects.append((r, act))

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for r, act in rects:
                    if r.collidepoint(ev.pos):
                        if act == "exit": pygame.quit(); sys.exit()
                        return act
        clock.tick(settings_module.FPS or 0)


def show_shop_menu():
    """Choose between Shop and Hats."""
    from ui.perma_shop import show_perma_shop
    from ui.hat_menu import show_hat_menu
    global _t
    while True:
        _t += 0.02
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)
        _draw_hex_bg(surf, sw, sh)
        _tick_particles(surf, sw, sh, _t)

        back_r, _ = _back_btn(surf, mx, my, small_font)

        # Title — centered
        title_y = sh//2 - 80
        _draw_text(surf, "SHOP & COSMETICS", menu_font, TEXT_BRIGHT, sw//2, title_y)

        # Buttons — centered under title
        bw, bh = 300, 50
        bx = sw//2 - bw//2
        sy = title_y + 35

        r1 = pygame.Rect(bx, sy, bw, bh)
        r2 = pygame.Rect(bx, sy + 64, bw, bh)
        _menu_btn(surf, r1, "Upgrades Shop", menu_font, mx, my)
        _menu_btn(surf, r2, "Cosmetics", menu_font, mx, my)

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if back_r.collidepoint(ev.pos): return
                if r1.collidepoint(ev.pos): show_perma_shop()
                if r2.collidepoint(ev.pos): show_hat_menu()
        clock.tick(settings_module.FPS or 0)


def show_play_mode():
    """Choose between Singleplayer and Multiplayer."""
    global _t
    while True:
        _t += 0.02
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)
        _draw_hex_bg(surf, sw, sh)
        _tick_particles(surf, sw, sh, _t)

        back_r, _ = _back_btn(surf, mx, my, small_font)

        title_y = sh//2 - 80
        _draw_text(surf, "PLAY", menu_font, TEXT_BRIGHT, sw//2, title_y)

        bw, bh = 300, 50
        bx = sw//2 - bw//2
        sy = title_y + 35

        r1 = pygame.Rect(bx, sy, bw, bh)
        r2 = pygame.Rect(bx, sy + 64, bw, bh)
        _menu_btn(surf, r1, "Singleplayer", menu_font, mx, my)
        _menu_btn(surf, r2, "Multiplayer", menu_font, mx, my)

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return "back"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if back_r.collidepoint(ev.pos): return "back"
                if r1.collidepoint(ev.pos): return "singleplayer"
                if r2.collidepoint(ev.pos): return "multiplayer"
        clock.tick(settings_module.FPS or 0)