# multiplayer_menus.py
"""Multiplayer menu and lobby — no unicode icons."""

import pygame, sys, socket, math
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

_t = 0.0

def _neon_btn(surf, rect, label, color, fnt, mx, my, t):
    hov = rect.collidepoint(mx, my)
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((*color[:3], 45 if hov else 10))
    surf.blit(bg, rect.topleft)
    gr = 6 if hov else 2
    for i in range(gr, 0, -1):
        a = int((16 if hov else 6)*i/gr)
        pygame.draw.rect(surf, (*color[:3], a), (rect.x-i, rect.y-i, rect.w+i*2, rect.h+i*2), 2, border_radius=5)
    pygame.draw.rect(surf, color, rect, 2 if not hov else 3, border_radius=5)
    txt = fnt.render(label, True, WHITE if hov else color)
    surf.blit(txt, (rect.centerx-txt.get_width()//2, rect.centery-txt.get_height()//2))
    return hov

def _hex_bg_light(surf, sw, sh, t):
    r = 55; hw = int(r*math.sqrt(3)); hh = r*2
    for row in range(-1, sh//int(hh*0.75)+3):
        for col in range(-1, sw//hw+3):
            x = col*hw+(row%2)*(hw//2); y = row*int(hh*0.75)
            p = math.sin(t*0.7+col*0.4+row*0.6)*0.5+0.5
            c = (int(p*8), int(5+p*14), int(15+p*22))
            pts = [(x+r*math.cos(math.radians(60*k-30)),
                     y+r*math.sin(math.radians(60*k-30))) for k in range(6)]
            pygame.draw.polygon(surf, c, pts, 1)


def show_multiplayer_menu():
    global _t
    ip_input = ""; input_active = False; status_msg = ""; status_color = WHITE

    while True:
        _t += 0.025
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill((3,3,12))
        _hex_bg_light(surf, sw, sh, _t)

        # Title
        tt = header_font.render("MULTIPLAYER", True, (0,255,255))
        gs2 = pygame.Surface((tt.get_width()+20, tt.get_height()+8), pygame.SRCALPHA)
        p = math.sin(_t*2)*0.3+0.6
        gs2.fill((0,255,255,int(12*p)))
        surf.blit(gs2, (sw//2-gs2.get_width()//2, 35))
        surf.blit(tt, (sw//2-tt.get_width()//2, 38))
        lw = int(150+math.sin(_t*1.5)*30)
        pygame.draw.line(surf, (0,255,255), (sw//2-lw//2, 82), (sw//2+lw//2, 82), 1)

        # Panel
        pw, ph = min(420, sw-40), 360
        px, py = sw//2-pw//2, 100
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8,8,20,190))
        surf.blit(panel, (px, py))
        pygame.draw.rect(surf, (0,255,255,50), (px,py,pw,ph), 1, border_radius=6)

        bw, bh = pw-36, 44
        bx = px+18
        cy = py+18

        # Singleplayer
        sp_r = pygame.Rect(bx, cy, bw, bh)
        _neon_btn(surf, sp_r, "Singleplayer", (57,255,20), menu_font, mx, my, _t)

        cy += 58
        # Host
        host_r = pygame.Rect(bx, cy, bw, bh)
        _neon_btn(surf, host_r, "Host Game", (0,200,255), menu_font, mx, my, _t)
        local_ip = get_local_ip()
        ip_lbl = small_font.render(f"Your IP: {local_ip}", True, (0,170,210))
        surf.blit(ip_lbl, (bx+bw//2-ip_lbl.get_width()//2, cy+bh+3))

        cy += 75
        # Join
        jl = small_font.render("JOIN BY IP", True, (100,110,130))
        surf.blit(jl, (bx, cy)); cy += 20

        ip_box = pygame.Rect(bx, cy, bw-100, 34)
        box_col = (255,200,50) if input_active else (70,80,100)
        bg2 = pygame.Surface((ip_box.w, ip_box.h), pygame.SRCALPHA)
        bg2.fill((*box_col[:3], 15 if not input_active else 25))
        surf.blit(bg2, ip_box.topleft)
        pygame.draw.rect(surf, box_col, ip_box, 2, border_radius=4)
        cursor = "|" if input_active and int(_t*4)%2==0 else ""
        it = menu_font.render(ip_input+cursor, True, WHITE)
        surf.blit(it, (ip_box.x+8, ip_box.centery-it.get_height()//2))

        join_r = pygame.Rect(bx+bw-92, cy, 92, 34)
        _neon_btn(surf, join_r, "Join", (255,165,0), menu_font, mx, my, _t)

        cy += 48
        if status_msg:
            st = small_font.render(status_msg, True, status_color)
            surf.blit(st, (sw//2-st.get_width()//2, cy))

        cy += 28
        back_r = pygame.Rect(bx, cy, bw, 36)
        _neon_btn(surf, back_r, "Back to Main Menu", (130,140,160), menu_font, mx, my, _t)

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return None, None
                if input_active:
                    if ev.key == pygame.K_RETURN:
                        ip = ip_input.strip()
                        if ip:
                            status_msg = f"Connecting to {ip}..."; status_color = (255,255,0)
                            display_mgr.present()
                            gs.net_client = GameClient()
                            if gs.net_client.connect(ip):
                                gs.net_mode = "client"; gs.net_client.send_username(gs.local_username)
                                return "client", gs.net_client
                            else: status_msg = "Connection failed!"; status_color = (255,30,60); gs.net_client = None
                    elif ev.key == pygame.K_BACKSPACE: ip_input = ip_input[:-1]
                    elif ev.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        try:
                            if not pygame.scrap.get_init(): pygame.scrap.init()
                            clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                            if clip: ip_input += clip.decode("utf-8",errors="ignore").replace("\x00","").strip()[:21-len(ip_input)]
                        except: pass
                    elif len(ip_input) < 21: ip_input += ev.unicode
            if ev.type == pygame.MOUSEBUTTONDOWN:
                input_active = ip_box.collidepoint(ev.pos)
                if sp_r.collidepoint(ev.pos): gs.net_mode = None; return "singleplayer", None
                if host_r.collidepoint(ev.pos):
                    gs.net_host = GameHost(); ip2 = gs.net_host.start(); gs.net_mode = "host"
                    status_msg = f"Hosting on {ip2}:{DEFAULT_PORT}"; status_color = (57,255,20)
                    return "host", gs.net_host
                if join_r.collidepoint(ev.pos):
                    ip = ip_input.strip()
                    if ip:
                        status_msg = f"Connecting to {ip}..."; status_color = (255,255,0)
                        display_mgr.present()
                        gs.net_client = GameClient()
                        if gs.net_client.connect(ip):
                            gs.net_mode = "client"; gs.net_client.send_username(gs.local_username)
                            return "client", gs.net_client
                        else: status_msg = "Connection failed!"; status_color = (255,30,60); gs.net_client = None
                if back_r.collidepoint(ev.pos): return None, None
        clock.tick(settings_module.FPS or 0)


def show_lobby():
    global _t
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80))
        local_ip = s.getsockname()[0]; s.close()
    except: local_ip = "Unknown"

    while True:
        _t += 0.025
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill((3,3,12))
        _hex_bg_light(surf, sw, sh, _t)

        tt = header_font.render("LOBBY", True, (0,255,255))
        gs2 = pygame.Surface((tt.get_width()+16, tt.get_height()+6), pygame.SRCALPHA)
        gs2.fill((0,255,255,10))
        surf.blit(gs2, (sw//2-gs2.get_width()//2, 32))
        surf.blit(tt, (sw//2-tt.get_width()//2, 35))

        pw, ph = min(420, sw-40), 300
        px, py = sw//2-pw//2, 90
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8,8,20,190))
        surf.blit(panel, (px, py))
        pygame.draw.rect(surf, (0,255,255,40), (px,py,pw,ph), 1, border_radius=6)

        cy = py+16
        if gs.net_mode == "host":
            it = menu_font.render("You are the HOST", True, (57,255,20))
            surf.blit(it, (sw//2-it.get_width()//2, cy)); cy += 28
            it2 = small_font.render(f"IP: {local_ip}  |  Share with friends!", True, (0,190,210))
            surf.blit(it2, (sw//2-it2.get_width()//2, cy)); cy += 26
            pc = 1+(len(gs.net_host.clients) if gs.net_host and hasattr(gs.net_host,'clients') else 0)
            pt = menu_font.render(f"Players: {pc}", True, WHITE)
            surf.blit(pt, (sw//2-pt.get_width()//2, cy)); cy += 30
            lbl = small_font.render(f"- {gs.local_username} (Host)", True, (57,255,20))
            surf.blit(lbl, (px+25, cy)); cy += 20
            if gs.net_host and hasattr(gs.net_host,'clients'):
                unames = gs.net_host.get_usernames()
                for cid in gs.net_host.clients:
                    un = unames.get(cid, f"Player{cid}")
                    cl = small_font.render(f"- {un}", True, (0,200,255))
                    surf.blit(cl, (px+25, cy)); cy += 20
        elif gs.net_mode == "client":
            it = menu_font.render("Connected!", True, (0,255,255))
            surf.blit(it, (sw//2-it.get_width()//2, cy)); cy += 28
            it2 = small_font.render("Waiting for host to start...", True, (100,110,130))
            surf.blit(it2, (sw//2-it2.get_width()//2, cy)); cy += 22
            it3 = small_font.render(f"You: {gs.local_username}", True, (255,200,50))
            surf.blit(it3, (sw//2-it3.get_width()//2, cy))

        bw2, bh2 = 240, 44
        bx2 = sw//2-bw2//2
        start_r = None
        if gs.net_mode == "host":
            start_r = pygame.Rect(bx2, sh-150, bw2, bh2)
            _neon_btn(surf, start_r, "START GAME", (57,255,20), menu_font, mx, my, _t)

        leave_r = pygame.Rect(bx2, sh-90, bw2, bh2)
        _neon_btn(surf, leave_r, "LEAVE", (255,30,60), menu_font, mx, my, _t)

        display_mgr.present()

        if gs.net_mode == "client" and gs.net_client:
            for msg in gs.net_client.get_messages():
                if msg.get("type") == MSG_GAME_START: return "start"

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return "leave"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if gs.net_mode == "host" and start_r and start_r.collidepoint(ev.pos):
                    if gs.net_host: gs.net_host.broadcast(MSG_GAME_START, {})
                    return "start"
                if leave_r.collidepoint(ev.pos): return "leave"
        clock.tick(settings_module.FPS or 0)