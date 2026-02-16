# multiplayer_menus.py
"""Multiplayer menu — host/join with server browser, lobby name, password."""

import pygame, sys, socket, json, math, time, threading
import core.settings as settings_module
from core.settings import *
from networking.net_common import *
from networking.net_host import GameHost
from networking.net_client import GameClient
from core.game_state import (
    display_mgr, clock, gs,
    header_font, title_font, menu_font, small_font, desc_font,
    GAME_NAME, VERSION
)

# ── Global standards ──
ACCENT = (0, 200, 255)
BG_DARK = (5, 6, 16)
PANEL_BG = (10, 12, 24)
TEXT_DIM = (60, 65, 80)
TEXT_MID = (130, 140, 160)
TEXT_BRIGHT = (220, 225, 240)
BORDER = (35, 40, 60)
GREEN = (57, 255, 20)
WHITE = (255, 255, 255)


def _back_btn(surf, mx, my):
    r = pygame.Rect(16, 16, 90, 34)
    hov = r.collidepoint(mx, my)
    c = ACCENT if hov else TEXT_DIM
    pygame.draw.rect(surf, c, r, 1 if not hov else 2, border_radius=5)
    t = small_font.render("< Back", True, TEXT_BRIGHT if hov else TEXT_MID)
    surf.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))
    return r


def _btn(surf, rect, label, mx, my, color=ACCENT, active=False):
    hov = rect.collidepoint(mx, my)
    if active:
        pygame.draw.rect(surf, (15, 22, 38), rect, 0, border_radius=6)
        pygame.draw.rect(surf, color, rect, 2, border_radius=6)
        txt = menu_font.render(label, True, color)
    elif hov:
        pygame.draw.rect(surf, (20, 25, 45), rect, 0, border_radius=6)
        pygame.draw.rect(surf, color, rect, 1, border_radius=6)
        txt = menu_font.render(label, True, TEXT_BRIGHT)
    else:
        pygame.draw.rect(surf, (12, 14, 26), rect, 0, border_radius=6)
        pygame.draw.rect(surf, BORDER, rect, 1, border_radius=6)
        txt = menu_font.render(label, True, TEXT_MID)
    surf.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
    return hov


def _text_input(surf, rect, text, active, mx, my, label="", cursor_tick=0):
    hov = rect.collidepoint(mx, my)
    bc = ACCENT if active else (BORDER if not hov else TEXT_DIM)
    pygame.draw.rect(surf, (15, 17, 30) if not active else (18, 22, 40), rect, 0, border_radius=5)
    pygame.draw.rect(surf, bc, rect, 1 if not active else 2, border_radius=5)
    if label:
        lt = desc_font.render(label, True, TEXT_DIM)
        surf.blit(lt, (rect.x, rect.y - 15))
    cursor = "|" if active and int(cursor_tick * 4) % 2 == 0 else ""
    tt = small_font.render(text + cursor, True, TEXT_BRIGHT if active else TEXT_MID)
    surf.blit(tt, (rect.x + 8, rect.centery - tt.get_height()//2))


# ── Server Discovery ──

class ServerScanner:
    """Listens for UDP broadcast beacons from LAN hosts."""
    def __init__(self):
        self.servers = {}  # {ip: {name, port, players, max, has_password, last_seen, ping}}
        self.lock = threading.Lock()
        self.running = False
        self._sock = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._sock:
            try: self._sock.close()
            except: pass

    def _listen(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except: pass
            self._sock.bind(("", BROADCAST_PORT))
            self._sock.settimeout(1.0)
        except Exception as e:
            print(f"[Scanner] Could not bind: {e}")
            return

        while self.running:
            try:
                data, addr = self._sock.recvfrom(2048)
                info = json.loads(data.decode("utf-8"))
                ip = info.get("ip", addr[0])
                now = time.time()
                with self.lock:
                    self.servers[ip] = {
                        "name": info.get("name", "Unknown"),
                        "port": info.get("port", DEFAULT_PORT),
                        "players": info.get("players", 1),
                        "max": info.get("max", 4),
                        "has_password": info.get("has_password", False),
                        "last_seen": now,
                        "ping": int((now % 1) * 100),  # Rough estimate
                    }
            except socket.timeout:
                pass
            except Exception:
                pass

        self._sock.close()

    def get_servers(self):
        now = time.time()
        with self.lock:
            # Remove stale servers (not seen for 5 seconds)
            self.servers = {k: v for k, v in self.servers.items() if now - v["last_seen"] < 5}
            return dict(self.servers)


# ── Multiplayer Menu ──

def show_multiplayer_menu():
    _t = 0.0
    tab = "browse"  # "browse" or "host" or "direct"
    # Host fields
    lobby_name = gs.local_username + "'s Game"
    password = ""
    # Direct connect
    ip_input = ""
    # Active input tracking
    active_field = None  # "lobby_name", "password", "ip", "direct_pw"
    status_msg = ""
    status_color = TEXT_MID
    direct_pw = ""

    scanner = ServerScanner()
    scanner.start()

    # Server browser state
    sort_key = "name"
    sort_reverse = False
    selected_server = None
    scroll_y = 0

    try:
        while True:
            _t += 0.025
            sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
            surf = display_mgr.get_screen()
            mx, my = pygame.mouse.get_pos()

            surf.fill(BG_DARK)

            # Back button
            back_r = _back_btn(surf, mx, my)

            # Title — smaller, not oversized
            tt = menu_font.render("MULTIPLAYER", True, TEXT_BRIGHT)
            surf.blit(tt, (sw//2 - tt.get_width()//2, 22))

            # Tabs — wider, centered, with proper gaps
            tabs = [("browse", "Browse"), ("host", "Host"), ("direct", "Join")]
            tab_w = 120
            total_tabs_w = len(tabs) * tab_w + (len(tabs) - 1) * 8
            tab_x = sw//2 - total_tabs_w//2
            tab_y = 52
            tab_rects = {}
            for i, (key, label) in enumerate(tabs):
                r = pygame.Rect(tab_x + i * (tab_w + 8), tab_y, tab_w, 30)
                tab_rects[key] = r
                _btn(surf, r, label, mx, my, ACCENT, active=(tab == key))

            # Content area
            content_y = 100
            content_h = sh - content_y - 20

            if tab == "browse":
                _draw_browser(surf, sw, sh, content_y, mx, my, _t, scanner, sort_key, sort_reverse,
                              selected_server, scroll_y, direct_pw, active_field, status_msg, status_color)

            elif tab == "host":
                _draw_host_panel(surf, sw, sh, content_y, mx, my, _t, lobby_name, password, active_field)

            elif tab == "direct":
                _draw_direct_panel(surf, sw, sh, content_y, mx, my, _t, ip_input, direct_pw, active_field, status_msg, status_color)

            display_mgr.present()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    scanner.stop(); pygame.quit(); sys.exit()

                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        if active_field:
                            active_field = None
                        else:
                            scanner.stop(); return "back", None
                    elif active_field:
                        if ev.key == pygame.K_TAB:
                            active_field = None
                        elif ev.key == pygame.K_BACKSPACE:
                            if active_field == "lobby_name": lobby_name = lobby_name[:-1]
                            elif active_field == "password": password = password[:-1]
                            elif active_field == "ip": ip_input = ip_input[:-1]
                            elif active_field == "direct_pw": direct_pw = direct_pw[:-1]
                            elif active_field == "browse_pw": direct_pw = direct_pw[:-1]
                        elif ev.key == pygame.K_RETURN:
                            if tab == "host" and active_field in ("lobby_name", "password"):
                                # Start hosting
                                gs.net_host = GameHost()
                                gs.net_host.lobby_name = lobby_name or "Game"
                                gs.net_host.password = password
                                ip2 = gs.net_host.start()
                                gs.net_mode = "host"
                                scanner.stop()
                                return "host", gs.net_host
                            elif tab == "direct" and active_field in ("ip", "direct_pw"):
                                result = _try_connect(ip_input.strip(), direct_pw)
                                if result:
                                    scanner.stop(); return result
                                else:
                                    status_msg = "Connection failed!"; status_color = (255, 50, 80)
                            elif tab == "browse" and active_field == "browse_pw":
                                if selected_server:
                                    result = _try_connect(selected_server, direct_pw)
                                    if result:
                                        scanner.stop(); return result
                                    else:
                                        status_msg = "Connection failed!"; status_color = (255, 50, 80)
                            active_field = None
                        elif ev.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            try:
                                if not pygame.scrap.get_init(): pygame.scrap.init()
                                clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                                if clip:
                                    txt = clip.decode("utf-8", errors="ignore").replace("\x00", "").strip()
                                    if active_field == "lobby_name": lobby_name += txt[:30 - len(lobby_name)]
                                    elif active_field == "password": password += txt[:20 - len(password)]
                                    elif active_field == "ip": ip_input += txt[:21 - len(ip_input)]
                                    elif active_field in ("direct_pw", "browse_pw"): direct_pw += txt[:20 - len(direct_pw)]
                            except: pass
                        else:
                            ch = ev.unicode
                            if ch and ch.isprintable():
                                if active_field == "lobby_name" and len(lobby_name) < 30: lobby_name += ch
                                elif active_field == "password" and len(password) < 20: password += ch
                                elif active_field == "ip" and len(ip_input) < 21: ip_input += ch
                                elif active_field in ("direct_pw", "browse_pw") and len(direct_pw) < 20: direct_pw += ch

                if ev.type == pygame.MOUSEWHEEL:
                    if tab == "browse":
                        scroll_y -= ev.y * 30

                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if back_r.collidepoint(ev.pos):
                        scanner.stop(); return "back", None

                    # Tab clicks
                    for key, r in tab_rects.items():
                        if r.collidepoint(ev.pos):
                            tab = key; active_field = None; status_msg = ""

                    if tab == "browse":
                        result = _handle_browser_click(ev.pos, sw, sh, content_y, scanner, sort_key,
                                                        sort_reverse, selected_server, scroll_y, direct_pw, active_field)
                        if result:
                            if result[0] == "sort":
                                if sort_key == result[1]:
                                    sort_reverse = not sort_reverse
                                else:
                                    sort_key = result[1]; sort_reverse = False
                            elif result[0] == "select":
                                selected_server = result[1]; direct_pw = ""
                            elif result[0] == "field":
                                active_field = result[1]
                            elif result[0] == "connect":
                                ip = result[1]
                                r2 = _try_connect(ip, direct_pw)
                                if r2:
                                    scanner.stop(); return r2
                                else:
                                    status_msg = "Connection failed!"; status_color = (255, 50, 80)

                    elif tab == "host":
                        # Check field clicks
                        cx, pw2 = sw//2 - 200, 400
                        cy = content_y + 20
                        name_r = pygame.Rect(cx, cy + 15, pw2, 32)
                        pw_r = pygame.Rect(cx, cy + 75, pw2, 32)
                        host_btn_r = pygame.Rect(cx, cy + 125, pw2, 40)
                        if name_r.collidepoint(ev.pos): active_field = "lobby_name"
                        elif pw_r.collidepoint(ev.pos): active_field = "password"
                        elif host_btn_r.collidepoint(ev.pos):
                            gs.net_host = GameHost()
                            gs.net_host.lobby_name = lobby_name or "Game"
                            gs.net_host.password = password
                            ip2 = gs.net_host.start()
                            gs.net_mode = "host"
                            scanner.stop()
                            return "host", gs.net_host
                        else:
                            active_field = None

                    elif tab == "direct":
                        cx, pw2 = sw//2 - 200, 400
                        cy = content_y + 20
                        ip_r = pygame.Rect(cx, cy + 15, pw2, 32)
                        dpw_r = pygame.Rect(cx, cy + 75, pw2, 32)
                        join_btn_r = pygame.Rect(cx, cy + 125, pw2, 40)
                        if ip_r.collidepoint(ev.pos): active_field = "ip"
                        elif dpw_r.collidepoint(ev.pos): active_field = "direct_pw"
                        elif join_btn_r.collidepoint(ev.pos):
                            result = _try_connect(ip_input.strip(), direct_pw)
                            if result:
                                scanner.stop(); return result
                            else:
                                status_msg = "Connection failed!"; status_color = (255, 50, 80)
                        else:
                            active_field = None

            clock.tick(settings_module.FPS or 0)
    finally:
        scanner.stop()


def _try_connect(ip, password=""):
    if not ip:
        return None
    gs.net_client = GameClient()
    if gs.net_client.connect(ip):
        gs.net_mode = "client"
        gs.net_client.send_username(gs.local_username)
        if password:
            gs.net_client.send("password", {"password": password})
        return "client", gs.net_client
    else:
        gs.net_client = None
        return None


# ── Drawing helpers ──

_browser_rects = {}  # Populated during draw, read during click

def _draw_browser(surf, sw, sh, content_y, mx, my, t, scanner, sort_key, sort_reverse,
                   selected_server, scroll_y, password, active_field, status_msg, status_color):
    global _browser_rects
    _browser_rects = {}

    servers = scanner.get_servers()
    server_list = list(servers.items())

    # Sort
    def sort_fn(item):
        ip, info = item
        if sort_key == "name": return info["name"].lower()
        elif sort_key == "players": return info["players"]
        elif sort_key == "ping": return info.get("ping", 999)
        elif sort_key == "password": return int(info.get("has_password", False))
        return info["name"].lower()

    server_list.sort(key=sort_fn, reverse=sort_reverse)

    # Table layout — centered
    table_w = min(sw - 80, 600)
    table_x = sw//2 - table_w//2
    cols = [
        ("password", "PW", 40),
        ("name", "Lobby Name", table_w - 240),
        ("players", "Players", 80),
        ("ping", "Ping", 70),
    ]

    # Column headers
    hdr_y = content_y
    col_x = table_x
    header_rects = {}
    for key, label, width in cols:
        r = pygame.Rect(col_x, hdr_y, width, 28)
        header_rects[key] = r
        _browser_rects[("sort", key)] = r
        hov = r.collidepoint(mx, my)
        indicator = " ▲" if sort_key == key and not sort_reverse else (" ▼" if sort_key == key else "")
        ht = small_font.render(label + indicator, True, ACCENT if (sort_key == key or hov) else TEXT_DIM)
        surf.blit(ht, (col_x + 4, hdr_y + 5))
        col_x += width + 10

    # Separator
    pygame.draw.line(surf, BORDER, (table_x, hdr_y + 30), (table_x + table_w, hdr_y + 30), 1)

    # Server rows
    row_h = 34
    row_y = hdr_y + 36
    max_visible = (sh - row_y - 80) // row_h
    max_scroll = max(0, len(server_list) - max_visible) * row_h
    scroll_y = max(0, min(scroll_y, max_scroll))

    if not server_list:
        nt = small_font.render("No servers found on LAN...", True, TEXT_DIM)
        surf.blit(nt, (sw//2 - nt.get_width()//2, row_y + 30))
        ip_hint = desc_font.render("Hosts on your network will appear here automatically", True, TEXT_DIM)
        surf.blit(ip_hint, (sw//2 - ip_hint.get_width()//2, row_y + 55))

    for i, (ip, info) in enumerate(server_list):
        y = row_y + i * row_h - scroll_y
        if y + row_h < row_y or y > sh - 60:
            continue

        row_rect = pygame.Rect(table_x, y, table_w, row_h - 2)
        _browser_rects[("select", ip)] = row_rect
        is_sel = (ip == selected_server)
        hov = row_rect.collidepoint(mx, my)

        if is_sel:
            pygame.draw.rect(surf, (15, 22, 38), row_rect, 0, border_radius=4)
            pygame.draw.rect(surf, ACCENT, row_rect, 1, border_radius=4)
        elif hov:
            pygame.draw.rect(surf, (14, 18, 32), row_rect, 0, border_radius=4)

        col_x = table_x
        for key, label, width in cols:
            if key == "password":
                icon = "🔒" if info.get("has_password") else ""
                ct = small_font.render(icon, True, (255, 200, 50) if icon else TEXT_DIM)
            elif key == "name":
                ct = small_font.render(info.get("name", "?"), True, TEXT_BRIGHT if is_sel else TEXT_MID)
            elif key == "players":
                ct = small_font.render(f"{info['players']}/{info['max']}", True, GREEN if info["players"] < info["max"] else (255, 80, 80))
            elif key == "ping":
                p = info.get("ping", "?")
                pc = GREEN if isinstance(p, int) and p < 50 else ((255, 200, 50) if isinstance(p, int) and p < 100 else (255, 80, 80))
                ct = small_font.render(f"{p}ms" if isinstance(p, int) else "?", True, pc)
            else:
                ct = small_font.render("?", True, TEXT_DIM)
            surf.blit(ct, (col_x + 6, y + row_h//2 - ct.get_height()//2))
            col_x += width + 10

    # Bottom: selected server info + join
    bottom_y = sh - 70
    if selected_server and selected_server in servers:
        info = servers[selected_server]
        # Password field if server has password
        if info.get("has_password"):
            pw_r = pygame.Rect(30, bottom_y, 200, 30)
            _browser_rects[("field", "browse_pw")] = pw_r
            _text_input(surf, pw_r, "*" * len(password), active_field == "browse_pw", mx, my, "Password:", t)

        join_x = 250 if info.get("has_password") else 30
        join_r = pygame.Rect(join_x, bottom_y, 140, 30)
        _browser_rects[("connect", selected_server)] = join_r
        _btn(surf, join_r, "Join Server", mx, my, GREEN)

        # Server IP
        ip_t = desc_font.render(f"IP: {selected_server}", True, TEXT_DIM)
        surf.blit(ip_t, (join_x + 155, bottom_y + 8))

    if status_msg:
        st = small_font.render(status_msg, True, status_color)
        surf.blit(st, (sw//2 - st.get_width()//2, bottom_y - 20))


def _handle_browser_click(pos, sw, sh, content_y, scanner, sort_key, sort_reverse, selected_server, scroll_y, pw, active_field):
    for key, rect in _browser_rects.items():
        if rect.collidepoint(pos):
            return key  # (action_type, value) tuple
    return None


def _draw_host_panel(surf, sw, sh, content_y, mx, my, t, lobby_name, password, active_field):
    cx = sw//2 - 200
    pw2 = 400
    cy = content_y + 20

    _text_input(surf, pygame.Rect(cx, cy + 15, pw2, 32), lobby_name, active_field == "lobby_name", mx, my, "Lobby Name:", t)
    _text_input(surf, pygame.Rect(cx, cy + 75, pw2, 32), "*" * len(password) if password else "", active_field == "password", mx, my, "Password (optional):", t)

    btn_r = pygame.Rect(cx, cy + 125, pw2, 40)
    _btn(surf, btn_r, "Start Hosting", mx, my, GREEN)

    # Info
    local_ip = get_local_ip()
    it = small_font.render(f"Your IP: {local_ip}:{DEFAULT_PORT}", True, TEXT_DIM)
    surf.blit(it, (cx, cy + 178))
    it2 = desc_font.render("Other players on your LAN will see this in the server browser", True, TEXT_DIM)
    surf.blit(it2, (cx, cy + 200))


def _draw_direct_panel(surf, sw, sh, content_y, mx, my, t, ip_input, password, active_field, status_msg, status_color):
    cx = sw//2 - 200
    pw2 = 400
    cy = content_y + 20

    _text_input(surf, pygame.Rect(cx, cy + 15, pw2, 32), ip_input, active_field == "ip", mx, my, "Host IP Address:", t)
    _text_input(surf, pygame.Rect(cx, cy + 75, pw2, 32), "*" * len(password) if password else "", active_field == "direct_pw", mx, my, "Password (if required):", t)

    btn_r = pygame.Rect(cx, cy + 125, pw2, 40)
    _btn(surf, btn_r, "Connect", mx, my, ACCENT)

    if status_msg:
        st = small_font.render(status_msg, True, status_color)
        surf.blit(st, (cx, cy + 178))


# ── Lobby ──

def show_lobby():
    _t = 0.0
    local_ip = get_local_ip()

    while True:
        _t += 0.025
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)

        back_r = _back_btn(surf, mx, my)

        tt = title_font.render("LOBBY", True, TEXT_BRIGHT)
        surf.blit(tt, (sw//2 - tt.get_width()//2, 12))

        # Panel
        pw, ph = min(480, sw - 40), 280
        px, py = sw//2 - pw//2, 60
        pygame.draw.rect(surf, PANEL_BG, (px, py, pw, ph), 0, border_radius=8)
        pygame.draw.rect(surf, BORDER, (px, py, pw, ph), 1, border_radius=8)

        cy = py + 16
        if gs.net_mode == "host":
            lobby = getattr(gs.net_host, 'lobby_name', 'Game') if gs.net_host else 'Game'
            lt = menu_font.render(f"Hosting: {lobby}", True, GREEN)
            surf.blit(lt, (sw//2 - lt.get_width()//2, cy)); cy += 28
            it2 = small_font.render(f"IP: {local_ip}:{DEFAULT_PORT}", True, TEXT_DIM)
            surf.blit(it2, (sw//2 - it2.get_width()//2, cy)); cy += 26
            pc = 1 + (len(gs.net_host.clients) if gs.net_host and hasattr(gs.net_host, 'clients') else 0)
            pt = menu_font.render(f"Players: {pc}", True, TEXT_BRIGHT)
            surf.blit(pt, (sw//2 - pt.get_width()//2, cy)); cy += 30

            lbl = small_font.render(f"• {gs.local_username} (Host)", True, GREEN)
            surf.blit(lbl, (px + 25, cy)); cy += 22
            if gs.net_host and hasattr(gs.net_host, 'clients'):
                unames = gs.net_host.get_usernames()
                for cid in gs.net_host.clients:
                    un = unames.get(cid, f"Player{cid}")
                    cl = small_font.render(f"• {un}", True, ACCENT)
                    surf.blit(cl, (px + 25, cy)); cy += 22

        elif gs.net_mode == "client":
            ct = menu_font.render("Connected!", True, ACCENT)
            surf.blit(ct, (sw//2 - ct.get_width()//2, cy)); cy += 28
            wt = small_font.render("Waiting for host to start...", True, TEXT_DIM)
            surf.blit(wt, (sw//2 - wt.get_width()//2, cy)); cy += 24
            ut = small_font.render(f"You: {gs.local_username}", True, (255, 200, 50))
            surf.blit(ut, (sw//2 - ut.get_width()//2, cy))

        # Buttons
        bw2, bh2 = 240, 40
        bx2 = sw//2 - bw2//2
        start_r = None
        if gs.net_mode == "host":
            start_r = pygame.Rect(bx2, sh - 120, bw2, bh2)
            _btn(surf, start_r, "START GAME", mx, my, GREEN)

        leave_r = pygame.Rect(bx2, sh - 65, bw2, bh2)
        _btn(surf, leave_r, "LEAVE", mx, my, (255, 60, 80))

        display_mgr.present()

        if gs.net_mode == "client" and gs.net_client:
            for msg in gs.net_client.get_messages():
                if msg.get("type") == MSG_GAME_START:
                    return "start"

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return "leave"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if back_r.collidepoint(ev.pos):
                    return "leave"
                if gs.net_mode == "host" and start_r and start_r.collidepoint(ev.pos):
                    if gs.net_host:
                        gs.net_host.broadcast(MSG_GAME_START, {})
                    return "start"
                if leave_r.collidepoint(ev.pos):
                    return "leave"
        clock.tick(settings_module.FPS or 0)