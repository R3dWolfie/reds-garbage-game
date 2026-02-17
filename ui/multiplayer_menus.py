# multiplayer_menus.py
"""Multiplayer menu — host/join with server browser, lobby name, password."""

import pygame, sys, socket, json, math, time, threading
import core.settings as settings_module
from core.settings import *
from networking.net_common import *
from networking.net_host import GameHost
from networking.net_client import GameClient
from networking.lobby_client import LobbyRegister, fetch_internet_servers
from networking.net_relay import create_relay_room, join_relay_room
import core.game_state as _gs
from core.game_state import (
    display_mgr, clock, gs,
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
    t = _gs.small_font.render("< Back", True, TEXT_BRIGHT if hov else TEXT_MID)
    surf.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))
    return r


def _btn(surf, rect, label, mx, my, color=ACCENT, active=False):
    hov = rect.collidepoint(mx, my)
    if active:
        pygame.draw.rect(surf, (15, 22, 38), rect, 0, border_radius=6)
        pygame.draw.rect(surf, color, rect, 2, border_radius=6)
        txt = _gs.menu_font.render(label, True, color)
    elif hov:
        pygame.draw.rect(surf, (20, 25, 45), rect, 0, border_radius=6)
        pygame.draw.rect(surf, color, rect, 1, border_radius=6)
        txt = _gs.menu_font.render(label, True, TEXT_BRIGHT)
    else:
        pygame.draw.rect(surf, (12, 14, 26), rect, 0, border_radius=6)
        pygame.draw.rect(surf, BORDER, rect, 1, border_radius=6)
        txt = _gs.menu_font.render(label, True, TEXT_MID)
    surf.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
    return hov


def _text_input(surf, rect, text, active, mx, my, label="", cursor_tick=0):
    hov = rect.collidepoint(mx, my)
    bc = ACCENT if active else (BORDER if not hov else TEXT_DIM)
    pygame.draw.rect(surf, (15, 17, 30) if not active else (18, 22, 40), rect, 0, border_radius=5)
    pygame.draw.rect(surf, bc, rect, 1 if not active else 2, border_radius=5)
    if label:
        lt = _gs.desc_font.render(label, True, TEXT_DIM)
        surf.blit(lt, (rect.x, rect.y - 15))
    cursor = "|" if active and int(cursor_tick * 4) % 2 == 0 else ""
    tt = _gs.small_font.render(text + cursor, True, TEXT_BRIGHT if active else TEXT_MID)
    surf.blit(tt, (rect.x + 8, rect.centery - tt.get_height()//2))


# ── Server Discovery ──

class ServerScanner:
    """Listens for UDP broadcast beacons from LAN hosts AND fetches internet servers."""
    def __init__(self):
        self.servers = {}  # {ip: {name, port, players, max, has_password, last_seen, ping, source}}
        self.lock = threading.Lock()
        self.running = False
        self._sock = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        self._inet_thread = threading.Thread(target=self._fetch_internet, daemon=True)
        self._inet_thread.start()

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
                        "ping": int((now % 1) * 100),
                        "source": "lan",
                    }
            except socket.timeout:
                pass
            except Exception:
                pass

        self._sock.close()

    def _fetch_internet(self):
        """Periodically fetch internet servers from the lobby API."""
        while self.running:
            try:
                inet_servers = fetch_internet_servers()
                now = time.time()
                with self.lock:
                    for srv in inet_servers:
                        ip = srv.get("ip", "")
                        port = srv.get("port", DEFAULT_PORT)
                        key = f"{ip}:{port}"
                        # Don't overwrite LAN entries (they have better ping info)
                        if ip in self.servers and self.servers[ip].get("source") == "lan":
                            continue
                        self.servers[key] = {
                            "name": srv.get("name", "Unknown"),
                            "port": port,
                            "players": srv.get("players", 1),
                            "max": srv.get("max_players", 4),
                            "has_password": srv.get("has_password", False),
                            "last_seen": now,
                            "ping": "?",
                            "source": "internet",
                        }
            except Exception as e:
                print(f"[Scanner] Internet fetch error: {e}")

            # Fetch every 5 seconds
            for _ in range(50):
                if not self.running:
                    return
                time.sleep(0.1)

    def get_servers(self):
        now = time.time()
        with self.lock:
            # Remove stale LAN servers (5s), keep internet servers longer (35s)
            self.servers = {k: v for k, v in self.servers.items()
                           if (v.get("source") == "internet" and now - v["last_seen"] < 35)
                           or (v.get("source") == "lan" and now - v["last_seen"] < 5)}
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
    active_field = None  # "lobby_name", "password", "ip", "direct_pw", "room_code"
    status_msg = ""
    status_color = TEXT_MID
    direct_pw = ""
    # Relay
    use_relay = True  # Default to relay (easier for users)
    room_code_input = ""
    max_players = 4

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
            tt = _gs.menu_font.render("MULTIPLAYER", True, TEXT_BRIGHT)
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
                _draw_host_panel(surf, sw, sh, content_y, mx, my, _t, lobby_name, password, active_field, use_relay, max_players, status_msg, status_color)

            elif tab == "direct":
                _draw_direct_panel(surf, sw, sh, content_y, mx, my, _t, ip_input, direct_pw, active_field, status_msg, status_color, room_code_input)

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
                            elif active_field == "room_code": room_code_input = room_code_input[:-1]
                        elif ev.key == pygame.K_RETURN:
                            if tab == "host" and active_field in ("lobby_name", "password"):
                                # Start hosting — delegates to click handler logic
                                pass  # Let user click the button
                            elif tab == "direct" and active_field == "room_code":
                                if room_code_input.strip():
                                    result = _try_relay_join(room_code_input.strip(), direct_pw)
                                    if result:
                                        scanner.stop(); return result
                                    else:
                                        status_msg = "Room not found!"; status_color = (255, 50, 80)
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
                                    elif active_field == "room_code": room_code_input += txt[:6 - len(room_code_input)].upper()
                            except: pass
                        else:
                            ch = ev.unicode
                            if ch and ch.isprintable():
                                if active_field == "lobby_name" and len(lobby_name) < 30: lobby_name += ch
                                elif active_field == "password" and len(password) < 20: password += ch
                                elif active_field == "ip" and len(ip_input) < 21: ip_input += ch
                                elif active_field in ("direct_pw", "browse_pw") and len(direct_pw) < 20: direct_pw += ch
                                elif active_field == "room_code" and len(room_code_input) < 6: room_code_input += ch.upper()

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
                                sname = ""
                                _srvs = scanner.get_servers()
                                if ip in _srvs:
                                    sname = _srvs[ip].get("name", "")
                                r2 = _try_connect(ip, direct_pw, server_name=sname)
                                if r2:
                                    scanner.stop(); return r2
                                else:
                                    status_msg = "Connection failed!"; status_color = (255, 50, 80)

                    elif tab == "host":
                        # Check field and button clicks
                        cx, pw2 = sw//2 - 200, 400
                        cy = content_y + 8
                        name_r = pygame.Rect(cx, cy + 15, pw2, 30)
                        pw_r = pygame.Rect(cx, cy + 65, pw2, 30)
                        relay_r = pygame.Rect(cx, cy + 132, pw2, 24)
                        host_btn_r = pygame.Rect(cx, cy + 164, pw2, 36)

                        # Check max_players buttons
                        _mp_handled = False
                        for key, rect in _browser_rects.items():
                            if rect.collidepoint(ev.pos) and key[0] == "max_players":
                                max_players = key[1]
                                _mp_handled = True
                                break

                        if _mp_handled:
                            pass
                        elif name_r.collidepoint(ev.pos): active_field = "lobby_name"
                        elif pw_r.collidepoint(ev.pos): active_field = "password"
                        elif relay_r.collidepoint(ev.pos): use_relay = not use_relay
                        elif host_btn_r.collidepoint(ev.pos):
                            gs.net_host = GameHost(max_players=max_players)
                            gs.net_host.lobby_name = lobby_name or "Game"
                            gs.net_host.password = password

                            if use_relay:
                                # Connect to relay server
                                status_msg = "Connecting to relay..."
                                status_color = (100, 200, 255)
                                relay_sock, result = create_relay_room(
                                    name=lobby_name or "Game",
                                    password=password,
                                    max_players=max_players,
                                )
                                if relay_sock:
                                    gs.net_host.start_relay(relay_sock, result)
                                    gs.net_mode = "host"
                                    gs._relay_code = result
                                    try:
                                        lobby_reg = LobbyRegister(
                                            lobby_name=lobby_name or "Game",
                                            port=DEFAULT_PORT,
                                            max_players=max_players,
                                            has_password=bool(password),
                                        )
                                        lobby_reg.start()
                                        gs._lobby_register = lobby_reg
                                    except Exception as e:
                                        print(f"[Lobby] Register failed: {e}")
                                    scanner.stop()
                                    return "host", gs.net_host
                                else:
                                    status_msg = f"Relay failed: {result}"
                                    status_color = (255, 50, 80)
                                    print(f"[Relay] Failed: {result}")
                            else:
                                # Direct P2P
                                ip2 = gs.net_host.start()
                                gs.net_mode = "host"
                                try:
                                    lobby_reg = LobbyRegister(
                                        lobby_name=lobby_name or "Game",
                                        port=DEFAULT_PORT,
                                        max_players=max_players,
                                        has_password=bool(password),
                                    )
                                    lobby_reg.start()
                                    gs._lobby_register = lobby_reg
                                except Exception as e:
                                    print(f"[Lobby] Register failed: {e}")
                                scanner.stop()
                                return "host", gs.net_host
                        else:
                            active_field = None

                    elif tab == "direct":
                        # Check recent server buttons first
                        _handled = False
                        for key, rect in _browser_rects.items():
                            if rect.collidepoint(ev.pos):
                                if key[0] == "connect_recent":
                                    # Check if it's a relay room code (6 chars, no dots)
                                    rkey = key[1]
                                    if len(rkey) == 6 and "." not in rkey:
                                        r2 = _try_relay_join(rkey, direct_pw)
                                    else:
                                        r2 = _try_connect(rkey, direct_pw)
                                    if r2:
                                        scanner.stop(); return r2
                                    else:
                                        status_msg = "Connection failed!"; status_color = (255, 50, 80)
                                    _handled = True; break
                                elif key[0] == "select_recent":
                                    ip_input = key[1]
                                    _handled = True; break
                        if not _handled:
                            cx, pw2 = sw//2 - 200, 400
                            cy = content_y + 10

                            # Room code field and button
                            rc_r = pygame.Rect(cx, cy + 24, pw2 - 120, 30)
                            rc_btn = pygame.Rect(cx + pw2 - 110, cy + 24, 110, 30)
                            if rc_r.collidepoint(ev.pos):
                                active_field = "room_code"
                            elif rc_btn.collidepoint(ev.pos):
                                if room_code_input.strip():
                                    r2 = _try_relay_join(room_code_input.strip(), direct_pw)
                                    if r2:
                                        scanner.stop(); return r2
                                    else:
                                        status_msg = "Room not found or connection failed!"; status_color = (255, 50, 80)
                            else:
                                # Calculate dynamic cy for rest of panel
                                recent = settings_module.config.get("recent_servers", [])
                                cy += 72  # room code section height (24 + 40 + 8)
                                if recent:
                                    cy += 20 + min(len(recent), 5) * 30 + 10
                                cy += 24  # "DIRECT CONNECT" label
                                ip_r = pygame.Rect(cx, cy + 18, pw2, 30)
                                dpw_r = pygame.Rect(cx, cy + 78, pw2, 30)
                                join_btn_r = pygame.Rect(cx, cy + 120, pw2, 38)
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


def _try_connect(ip, password="", port=None, server_name=""):
    if not ip:
        return None
    # Handle ip:port format
    connect_ip = ip
    connect_port = port or DEFAULT_PORT
    if ":" in ip:
        parts = ip.rsplit(":", 1)
        connect_ip = parts[0]
        try:
            connect_port = int(parts[1])
        except ValueError:
            pass
    gs.net_client = GameClient()
    if gs.net_client.connect(connect_ip, connect_port):
        gs.net_mode = "client"
        gs.net_client.send_username(gs.local_username)
        if password:
            gs.net_client.send("password", {"password": password})
        # Save to recent servers
        _save_recent_server(connect_ip, connect_port, server_name or connect_ip)
        return "client", gs.net_client
    else:
        gs.net_client = None
        return None


def _try_relay_join(room_code, password=""):
    """Join a relay room by code. Returns ("client", client) on success, None on failure."""
    if not room_code:
        return None
    relay_sock, err = join_relay_room(room_code, password=password)
    if relay_sock is None:
        print(f"[Relay] Join failed: {err}")
        return None
    gs.net_client = GameClient()
    if gs.net_client.connect_relay(relay_sock):
        gs.net_mode = "client"
        gs.net_client.send_username(gs.local_username)
        # Save to recent with room code as key
        _save_recent_server(room_code, 0, f"Relay: {room_code}")
        return "client", gs.net_client
    else:
        gs.net_client = None
        return None


def _save_recent_server(ip, port, name):
    """Save a server to the recent servers list in config."""
    import time as _time
    recent = settings_module.config.get("recent_servers", [])
    key = f"{ip}:{port}"
    # Remove duplicates
    recent = [s for s in recent if s.get("key") != key]
    # Add to front
    recent.insert(0, {
        "key": key,
        "ip": ip,
        "port": port,
        "name": name,
        "last_joined": int(_time.time()),
    })
    # Keep max 10
    recent = recent[:10]
    settings_module.config["recent_servers"] = recent
    from core.settings import save_config
    save_config(settings_module.config)


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
        elif sort_key == "ping": return info.get("ping", 999) if isinstance(info.get("ping"), int) else 999
        elif sort_key == "password": return int(info.get("has_password", False))
        return info["name"].lower()

    server_list.sort(key=sort_fn, reverse=sort_reverse)

    # Table layout — centered
    table_w = min(sw - 80, 600)
    table_x = sw//2 - table_w//2

    y_cursor = content_y

    # ── Live Servers Section ──
    sec_lbl2 = _gs.small_font.render("SERVERS", True, TEXT_DIM)
    surf.blit(sec_lbl2, (table_x, y_cursor + 2))
    y_cursor += 20

    cols = [
        ("password", "PW", 30),
        ("name", "Lobby Name", table_w - 280),
        ("players", "Players", 70),
        ("ping", "Ping", 55),
        ("source", "Source", 60),
    ]

    # Column headers
    hdr_y = y_cursor
    col_x = table_x
    for key, label, width in cols:
        r = pygame.Rect(col_x, hdr_y, width, 24)
        _browser_rects[("sort", key)] = r
        hov = r.collidepoint(mx, my)
        indicator = " ^" if sort_key == key and not sort_reverse else (" v" if sort_key == key else "")
        ht = _gs.desc_font.render(label + indicator, True, ACCENT if (sort_key == key or hov) else TEXT_DIM)
        surf.blit(ht, (col_x + 4, hdr_y + 4))
        col_x += width + 8

    pygame.draw.line(surf, BORDER, (table_x, hdr_y + 26), (table_x + table_w, hdr_y + 26), 1)

    # Server rows
    row_h = 32
    row_y = hdr_y + 30
    max_visible = (sh - row_y - 80) // row_h
    max_scroll = max(0, len(server_list) - max_visible) * row_h
    scroll_y = max(0, min(scroll_y, max_scroll))

    if not server_list:
        nt = _gs.small_font.render("Searching for servers...", True, TEXT_DIM)
        surf.blit(nt, (sw//2 - nt.get_width()//2, row_y + 20))
        ip_hint = _gs.desc_font.render("LAN and internet servers will appear here", True, TEXT_DIM)
        surf.blit(ip_hint, (sw//2 - ip_hint.get_width()//2, row_y + 42))

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
                icon = "[PW]" if info.get("has_password") else ""
                ct = _gs.small_font.render(icon, True, (255, 200, 50) if icon else TEXT_DIM)
            elif key == "name":
                ct = _gs.small_font.render(info.get("name", "?"), True, TEXT_BRIGHT if is_sel else TEXT_MID)
            elif key == "players":
                ct = _gs.small_font.render(f"{info['players']}/{info['max']}", True, GREEN if info["players"] < info["max"] else (255, 80, 80))
            elif key == "ping":
                p = info.get("ping", "?")
                pc = GREEN if isinstance(p, int) and p < 50 else ((255, 200, 50) if isinstance(p, int) and p < 100 else (255, 80, 80))
                ct = _gs.small_font.render(f"{p}ms" if isinstance(p, int) else "?", True, pc)
            elif key == "source":
                src = info.get("source", "lan")
                sc = (100, 200, 255) if src == "internet" else (100, 255, 100)
                ct = _gs.desc_font.render("NET" if src == "internet" else "LAN", True, sc)
            else:
                ct = _gs.small_font.render("?", True, TEXT_DIM)
            surf.blit(ct, (col_x + 4, y + row_h//2 - ct.get_height()//2))
            col_x += width + 8

    # Bottom: selected server info + join
    bottom_y = sh - 70
    if selected_server:
        # Check if it's a live server or recent
        info = servers.get(selected_server, None)
        is_recent = not info
        if info and info.get("has_password"):
            pw_r = pygame.Rect(30, bottom_y, 200, 30)
            _browser_rects[("field", "browse_pw")] = pw_r
            _text_input(surf, pw_r, "*" * len(password), active_field == "browse_pw", mx, my, "Password:", t)

        join_x = 250 if (info and info.get("has_password")) else 30
        join_r = pygame.Rect(join_x, bottom_y, 140, 30)
        _browser_rects[("connect", selected_server)] = join_r
        _btn(surf, join_r, "Join Server", mx, my, GREEN)

        # Server IP
        ip_t = _gs.desc_font.render(f"IP: {selected_server}", True, TEXT_DIM)
        surf.blit(ip_t, (join_x + 155, bottom_y + 8))

    if status_msg:
        st = _gs.small_font.render(status_msg, True, status_color)
        surf.blit(st, (sw//2 - st.get_width()//2, bottom_y - 20))


def _handle_browser_click(pos, sw, sh, content_y, scanner, sort_key, sort_reverse, selected_server, scroll_y, pw, active_field):
    for key, rect in _browser_rects.items():
        if rect.collidepoint(pos):
            return key  # (action_type, value) tuple
    return None


def _draw_host_panel(surf, sw, sh, content_y, mx, my, t, lobby_name, password, active_field, use_relay=False, max_players=4, status_msg="", status_color=TEXT_MID):
    global _browser_rects
    cx = sw//2 - 200
    pw2 = 400
    cy = content_y + 8

    _text_input(surf, pygame.Rect(cx, cy + 15, pw2, 30), lobby_name, active_field == "lobby_name", mx, my, "Lobby Name:", t)
    _text_input(surf, pygame.Rect(cx, cy + 65, pw2, 30), "*" * len(password) if password else "", active_field == "password", mx, my, "Password (optional):", t)

    # Max players — inline row
    mp_label = _gs.desc_font.render("Max Players:", True, TEXT_DIM)
    surf.blit(mp_label, (cx, cy + 105))
    for i, count in enumerate([2, 3, 4, 6, 8]):
        bx = cx + 80 + i * 42
        br = pygame.Rect(bx, cy + 103, 36, 22)
        _browser_rects[("max_players", count)] = br
        is_sel = (max_players == count)
        hov = br.collidepoint(mx, my)
        bc = ACCENT if is_sel else (TEXT_DIM if hov else BORDER)
        pygame.draw.rect(surf, (15, 22, 38) if is_sel else (12, 14, 26), br, 0, border_radius=3)
        pygame.draw.rect(surf, bc, br, 2 if is_sel else 1, border_radius=3)
        ct = _gs.small_font.render(str(count), True, ACCENT if is_sel else (TEXT_BRIGHT if hov else TEXT_MID))
        surf.blit(ct, (br.centerx - ct.get_width()//2, br.centery - ct.get_height()//2))

    # Relay toggle — compact
    relay_y = cy + 132
    relay_r = pygame.Rect(cx, relay_y, pw2, 24)
    _browser_rects[("toggle", "relay")] = relay_r
    relay_hov = relay_r.collidepoint(mx, my)
    pygame.draw.rect(surf, (18, 22, 40) if relay_hov else (12, 14, 26), relay_r, 0, border_radius=4)
    pygame.draw.rect(surf, ACCENT if use_relay else BORDER, relay_r, 1 if not use_relay else 2, border_radius=4)
    cb_x, cb_y = cx + 6, relay_y + 4
    pygame.draw.rect(surf, ACCENT if use_relay else BORDER, (cb_x, cb_y, 14, 14), 2 if use_relay else 1, border_radius=2)
    if use_relay:
        pygame.draw.line(surf, ACCENT, (cb_x + 3, cb_y + 7), (cb_x + 6, cb_y + 10), 2)
        pygame.draw.line(surf, ACCENT, (cb_x + 6, cb_y + 10), (cb_x + 11, cb_y + 3), 2)
    rl = _gs.small_font.render("Use Relay (no port forwarding needed)", True, ACCENT if use_relay else TEXT_MID)
    surf.blit(rl, (cb_x + 20, relay_y + 4))

    # Host button
    btn_r = pygame.Rect(cx, cy + 164, pw2, 36)
    btn_label = "Start Hosting (Relay)" if use_relay else "Start Hosting (Direct)"
    _btn(surf, btn_r, btn_label, mx, my, GREEN)

    # Status / info — single line
    info_y = cy + 208
    if status_msg:
        st = _gs.small_font.render(status_msg, True, status_color)
        surf.blit(st, (cx, info_y))
        info_y += 18
    if use_relay:
        it = _gs.desc_font.render("Room code — no IP or port forwarding needed.", True, TEXT_DIM)
        surf.blit(it, (cx, info_y))
    else:
        local_ip = get_local_ip()
        it = _gs.desc_font.render(f"Your IP: {local_ip}:{DEFAULT_PORT}  —  Port forwarding may be required.", True, TEXT_DIM)
        surf.blit(it, (cx, info_y))


def _draw_direct_panel(surf, sw, sh, content_y, mx, my, t, ip_input, password, active_field, status_msg, status_color, room_code_input=""):
    global _browser_rects
    cx = sw//2 - 200
    pw2 = 400
    cy = content_y + 10

    # ── Room Code Section ──
    sec_lbl0 = _gs.small_font.render("JOIN BY ROOM CODE", True, TEXT_DIM)
    surf.blit(sec_lbl0, (cx, cy))
    cy += 24

    # Room code input (no label — section header serves as label)
    rc_input_r = pygame.Rect(cx, cy, pw2 - 120, 30)
    _text_input(surf, rc_input_r, room_code_input.upper(), active_field == "room_code", mx, my, "", t)
    # Placeholder text if empty
    if not room_code_input and active_field != "room_code":
        ph = _gs.desc_font.render("Enter 6-letter code...", True, TEXT_DIM)
        surf.blit(ph, (cx + 8, cy + 7))
    relay_btn_r = pygame.Rect(cx + pw2 - 110, cy, 110, 30)
    _btn(surf, relay_btn_r, "Join Room", mx, my, (100, 200, 255))
    cy += 40

    pygame.draw.line(surf, BORDER, (cx, cy), (cx + pw2, cy), 1)
    cy += 8

    # ── Recent Servers Section ──
    recent = settings_module.config.get("recent_servers", [])
    if recent:
        sec_lbl = _gs.small_font.render("RECENTLY JOINED", True, TEXT_DIM)
        surf.blit(sec_lbl, (cx, cy))
        cy += 20

        for ri, rsrv in enumerate(recent[:5]):
            row_rect = pygame.Rect(cx, cy, pw2, 28)
            _browser_rects[("select_recent", rsrv["key"])] = row_rect
            hov = row_rect.collidepoint(mx, my)
            if hov:
                pygame.draw.rect(surf, (14, 18, 32), row_rect, 0, border_radius=4)

            # Server name
            name_t = _gs.small_font.render(rsrv.get("name", rsrv["key"]), True, (255, 200, 50) if hov else TEXT_MID)
            surf.blit(name_t, (cx + 8, cy + 5))

            # IP:port or room code on the right
            key_label = rsrv["key"]
            ip_t = _gs.desc_font.render(key_label, True, TEXT_DIM)
            surf.blit(ip_t, (cx + pw2 - ip_t.get_width() - 76, cy + 7))

            # Quick join button
            qr = pygame.Rect(cx + pw2 - 66, cy + 2, 58, 24)
            _browser_rects[("connect_recent", rsrv["key"])] = qr
            qhov = qr.collidepoint(mx, my)
            pygame.draw.rect(surf, GREEN if qhov else BORDER, qr, 1 if not qhov else 2, border_radius=4)
            qt = _gs.desc_font.render("Join", True, GREEN if qhov else TEXT_DIM)
            surf.blit(qt, (qr.centerx - qt.get_width()//2, qr.centery - qt.get_height()//2))

            cy += 30

        pygame.draw.line(surf, BORDER, (cx, cy + 2), (cx + pw2, cy + 2), 1)
        cy += 10

    # ── Direct Connect Section ──
    sec_lbl2 = _gs.small_font.render("DIRECT CONNECT (IP)", True, TEXT_DIM)
    surf.blit(sec_lbl2, (cx, cy))
    cy += 24

    _text_input(surf, pygame.Rect(cx, cy + 18, pw2, 30), ip_input, active_field == "ip", mx, my, "Host IP Address:", t)
    _text_input(surf, pygame.Rect(cx, cy + 78, pw2, 30), "*" * len(password) if password else "", active_field == "direct_pw", mx, my, "Password (if required):", t)

    btn_r = pygame.Rect(cx, cy + 120, pw2, 38)
    _btn(surf, btn_r, "Connect", mx, my, ACCENT)

    if status_msg:
        st = _gs.small_font.render(status_msg, True, status_color)
        surf.blit(st, (cx, cy + 165))


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

        tt = _gs.title_font.render("LOBBY", True, TEXT_BRIGHT)
        surf.blit(tt, (sw//2 - tt.get_width()//2, 12))

        # Panel
        pw, ph = min(480, sw - 40), 280
        px, py = sw//2 - pw//2, 60
        pygame.draw.rect(surf, PANEL_BG, (px, py, pw, ph), 0, border_radius=8)
        pygame.draw.rect(surf, BORDER, (px, py, pw, ph), 1, border_radius=8)

        cy = py + 16
        if gs.net_mode == "host":
            lobby = getattr(gs.net_host, 'lobby_name', 'Game') if gs.net_host else 'Game'
            lt = _gs.menu_font.render(f"Hosting: {lobby}", True, GREEN)
            surf.blit(lt, (sw//2 - lt.get_width()//2, cy)); cy += 28

            # Show relay code or IP
            relay_code = getattr(gs, '_relay_code', None) or getattr(gs.net_host, '_relay_code', None)
            if relay_code:
                code_t = _gs.menu_font.render(f"Room Code: {relay_code}", True, (100, 200, 255))
                surf.blit(code_t, (sw//2 - code_t.get_width()//2, cy)); cy += 26
                hint_t = _gs.desc_font.render("Share this code with friends to join", True, TEXT_DIM)
                surf.blit(hint_t, (sw//2 - hint_t.get_width()//2, cy)); cy += 20
            else:
                it2 = _gs.small_font.render(f"IP: {local_ip}:{DEFAULT_PORT}", True, TEXT_DIM)
                surf.blit(it2, (sw//2 - it2.get_width()//2, cy)); cy += 26

            pc = 1 + (len(gs.net_host.clients) if gs.net_host and hasattr(gs.net_host, 'clients') else 0)
            pt = _gs.menu_font.render(f"Players: {pc}", True, TEXT_BRIGHT)
            surf.blit(pt, (sw//2 - pt.get_width()//2, cy)); cy += 30

            lbl = _gs.small_font.render(f"• {gs.local_username} (Host)", True, GREEN)
            surf.blit(lbl, (px + 25, cy)); cy += 22
            if gs.net_host and hasattr(gs.net_host, 'clients'):
                unames = gs.net_host.get_usernames()
                for cid in gs.net_host.clients:
                    un = unames.get(cid, f"Player{cid}")
                    cl = _gs.small_font.render(f"• {un}", True, ACCENT)
                    surf.blit(cl, (px + 25, cy)); cy += 22

        elif gs.net_mode == "client":
            ct = _gs.menu_font.render("Connected!", True, ACCENT)
            surf.blit(ct, (sw//2 - ct.get_width()//2, cy)); cy += 28
            wt = _gs.small_font.render("Waiting for host to start...", True, TEXT_DIM)
            surf.blit(wt, (sw//2 - wt.get_width()//2, cy)); cy += 24
            ut = _gs.small_font.render(f"You: {gs.local_username}", True, (255, 200, 50))
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