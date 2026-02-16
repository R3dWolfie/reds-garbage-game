# main.py
import pygame
import sys
import random
import math
import settings as settings_module
from settings import *
from player_default import PlayerDefault
from player_tank import PlayerTank
from player_laser import PlayerLaser
from enemy import Enemy, Boss
from objects import Bullet, LaserBeam, ExpGem, HealthOrb
from networking.net_common import *
from networking.net_host import GameHost
from networking.net_client import GameClient
from updater.version import GAME_NAME, VERSION
from sprite_loader import load_sprite
from sound_manager import SoundManager

# ---- Additional message types not in net_common ----
MSG_PARTY_LEVEL_UP = "party_level_up"
MSG_UPGRADE_PAUSE = "upgrade_pause"
MSG_UPGRADE_RESUME = "upgrade_resume"
MSG_WAVE_COMPLETE = "wave_complete"
MSG_ENEMY_DEAD = "enemy_dead"
MSG_ORB_SPAWN = "orb_spawn"
MSG_USERNAME = "username"

# ---- Global network state ----
net_host = None
net_client = None
net_mode = None  # "host", "client", or None (singleplayer)
remote_players = {}  # {player_id: {" x": ..., "y": ..., "class": ..., "level": ...}}
remote_enemies = {}  # {enemy_id: RemoteEnemyGhost}
upgrade_paused_by = None  # None or {"player_name": str, "level": int} when someone is upgrading
local_username = settings_module.config.get("username", "Player")

# ---- Initialize ----
pygame.init()
pygame.mixer.init()

# Class registry
PLAYER_CLASSES = {
    "default": PlayerDefault,
    "tank": PlayerTank,
    "laser": PlayerLaser,
}


# ===========================================================
#                   DISPLAY MANAGER
# ===========================================================

class DisplayManager:
    def __init__(self):
        self.config = settings_module.config
        self.screen = None
        self.apply()

    def apply(self):
        w, h = self.config["resolution"]

        if self.config["fullscreen"]:
            # SCALED flag makes pygame render at (w,h) but scale to fill the monitor
            # Mouse coordinates are automatically mapped back to (w,h) space
            self.screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN | pygame.SCALED)
        else:
            self.screen = pygame.display.set_mode((w, h))

        pygame.display.set_caption("Red's Garbage Game")
        settings_module.SCREEN_WIDTH = w
        settings_module.SCREEN_HEIGHT = h
        global SCREEN_WIDTH, SCREEN_HEIGHT
        SCREEN_WIDTH = w
        SCREEN_HEIGHT = h

    def set_resolution(self, res):
        self.config["resolution"] = list(res)
        self.apply()

    def toggle_fullscreen(self):
        self.config["fullscreen"] = not self.config["fullscreen"]
        self.apply()

    def set_fullscreen(self, val):
        self.config["fullscreen"] = val
        self.apply()

    def get_screen(self):
        return self.screen

    def get_resolution(self):
        return (settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT)


display_mgr = DisplayManager()
screen = display_mgr.get_screen()

# Scrap (clipboard) requires a display to exist first
try:
    pygame.scrap.init()
except Exception:
    pass

# Sound manager — generates all SFX procedurally
sounds = SoundManager(settings_module.config)

# Screen shake state (global so any function can trigger it)
_shake_frames = 0
_shake_intensity = 0


def trigger_shake(frames=6, intensity=5):
    global _shake_frames, _shake_intensity
    _shake_frames = max(_shake_frames, frames)
    _shake_intensity = max(_shake_intensity, intensity)


clock = pygame.time.Clock()

# Fonts
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 14)
title_font = pygame.font.SysFont("Arial", 40)
boss_font = pygame.font.SysFont("Arial", 30, bold=True)
menu_font = pygame.font.SysFont("Arial", 24)
header_font = pygame.font.SysFont("Arial", 50, bold=True)
desc_font = pygame.font.SysFont("Arial", 16, italic=True)


# ===========================================================
#                   SETTINGS MENU
# ===========================================================

class SettingsMenu:
    def __init__(self, dm):
        self.dm = dm
        self.active = False
        current_res = tuple(self.dm.config["resolution"])
        self.res_index = RESOLUTIONS.index(current_res) if current_res in RESOLUTIONS else 2
        self.dragging = None

    def open(self):
        self.active = True
        current_res = tuple(self.dm.config["resolution"])
        if current_res in RESOLUTIONS:
            self.res_index = RESOLUTIONS.index(current_res)

    def close(self):
        self.active = False
        self.dragging = None

    def _draw_slider(self, surf, x, y, width, value, label, key):
        txt = menu_font.render(f"{label}: {int(value * 100)}%", True, WHITE)
        surf.blit(txt, (x, y))
        track_y = y + 30
        track_rect = pygame.Rect(x, track_y, width, 10)
        pygame.draw.rect(surf, DARK_GRAY, track_rect)
        fill_w = int(width * value)
        pygame.draw.rect(surf, GREEN, (x, track_y, fill_w, 10))
        pygame.draw.rect(surf, WHITE, track_rect, 2)
        handle_rect = pygame.Rect(x + fill_w - 8, track_y - 5, 16, 20)
        pygame.draw.rect(surf, GOLD, handle_rect)
        pygame.draw.rect(surf, WHITE, handle_rect, 2)
        return track_rect, key

    def _draw_button(self, surf, rect, text, color=DARK_GRAY, text_color=WHITE, border_color=WHITE):
        mx, my = pygame.mouse.get_pos()
        c = GRAY if rect.collidepoint(mx, my) else color
        pygame.draw.rect(surf, c, rect)
        pygame.draw.rect(surf, border_color, rect, 2)
        txt = menu_font.render(text, True, text_color)
        surf.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        return rect

    def run(self, background_surf):
        self.open()
        while self.active:
            sw = self.dm.config["resolution"][0]
            sh = self.dm.config["resolution"][1]
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit();
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.close();
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for sr, sk in self.slider_rects:
                        if sr.inflate(0, 20).collidepoint(mx, my):
                            self.dragging = sk
                    if self.left_arrow.collidepoint(mx, my):
                        self.res_index = (self.res_index - 1) % len(RESOLUTIONS)
                    if self.right_arrow.collidepoint(mx, my):
                        self.res_index = (self.res_index + 1) % len(RESOLUTIONS)
                    if self.apply_btn.collidepoint(mx, my):
                        self.dm.set_resolution(RESOLUTIONS[self.res_index])
                    if self.fs_btn.collidepoint(mx, my):
                        self.dm.toggle_fullscreen()
                    if self.back_btn.collidepoint(mx, my):
                        self.close();
                        return
                    if self.exit_btn.collidepoint(mx, my):
                        pygame.quit();
                        sys.exit()
                if event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = None

            if self.dragging:
                for sr, sk in self.slider_rects:
                    if sk == self.dragging:
                        val = max(0.0, min(1.0, (mx - sr.x) / sr.width))
                        if sk == "master":
                            self.dm.set_master_volume(val)
                        elif sk == "sfx":
                            self.dm.set_sfx_volume(val)
                        elif sk == "music":
                            self.dm.set_music_volume(val)

            surf = self.dm.get_screen()
            if background_surf:
                surf.blit(background_surf, (0, 0))
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            surf.blit(overlay, (0, 0))

            title = header_font.render("SETTINGS", True, GOLD)
            surf.blit(title, (sw // 2 - title.get_width() // 2, 30))

            px, py = sw // 2 - 250, 90
            pw, ph = 500, 520
            pygame.draw.rect(surf, (30, 30, 30), (px, py, pw, ph))
            pygame.draw.rect(surf, GOLD, (px, py, pw, ph), 2)

            cx, cy = px + 30, py + 20
            slider_w = pw - 60

            res_label = menu_font.render("Resolution:", True, WHITE)
            surf.blit(res_label, (cx, cy))
            res_str = f"{RESOLUTIONS[self.res_index][0]} x {RESOLUTIONS[self.res_index][1]}"
            res_text = menu_font.render(res_str, True, GOLD)
            self.left_arrow = self._draw_button(surf, pygame.Rect(cx + 150, cy - 2, 35, 30), "<", border_color=GOLD)
            surf.blit(res_text, (cx + 200, cy))
            self.right_arrow = self._draw_button(surf,
                                                 pygame.Rect(cx + 200 + res_text.get_width() + 15, cy - 2, 35, 30), ">",
                                                 border_color=GOLD)

            cy += 40
            self.apply_btn = self._draw_button(surf, pygame.Rect(cx, cy, 180, 35), "Apply Resolution",
                                               border_color=GREEN, text_color=GREEN)

            cy += 50
            fs = "ON" if self.dm.config["fullscreen"] else "OFF"
            fc = GREEN if self.dm.config["fullscreen"] else RED
            self.fs_btn = self._draw_button(surf, pygame.Rect(cx, cy, 250, 35), f"Fullscreen: {fs}", border_color=fc,
                                            text_color=fc)

            cy += 60
            self.slider_rects = []
            t, k = self._draw_slider(surf, cx, cy, slider_w, self.dm.config["master_volume"], "Master Volume", "master")
            self.slider_rects.append((t, k))
            cy += 70
            t, k = self._draw_slider(surf, cx, cy, slider_w, self.dm.config["sfx_volume"], "SFX Volume", "sfx")
            self.slider_rects.append((t, k))
            cy += 70
            t, k = self._draw_slider(surf, cx, cy, slider_w, self.dm.config["music_volume"], "Music Volume", "music")
            self.slider_rects.append((t, k))

            cy += 80
            self.back_btn = self._draw_button(surf, pygame.Rect(cx, cy, 200, 40), "Back", border_color=WHITE)
            self.exit_btn = self._draw_button(surf, pygame.Rect(cx + 230, cy, 200, 40), "Exit Game", border_color=RED,
                                              text_color=RED)

            pygame.display.flip()
            clock.tick(30)


settings_menu = SettingsMenu(display_mgr)


# ===========================================================
#                   CLASS SELECTION SCREEN
# ===========================================================

def show_class_selection():
    """Let the player pick a class. Returns the class key string."""
    global net_mode, net_host, net_client
    class_keys = list(CLASS_INFO.keys())

    # Track if we're in multiplayer and waiting for others
    waiting_for_players = False
    players_ready = set()  # Set of player IDs who have chosen

    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BLACK)

        # Title
        if waiting_for_players:
            title = header_font.render("WAITING FOR PLAYERS...", True, CYAN)
        else:
            title = header_font.render("CHOOSE YOUR CLASS", True, GOLD)
        surf.blit(title, (sw // 2 - title.get_width() // 2, 40))

        # Class cards
        card_w = 280
        card_h = 350
        total_w = len(class_keys) * card_w + (len(class_keys) - 1) * 30
        start_x = sw // 2 - total_w // 2

        card_rects = []
        for i, key in enumerate(class_keys):
            info = CLASS_INFO[key]
            cx = start_x + i * (card_w + 30)
            cy = sh // 2 - card_h // 2 - 10

            card_rect = pygame.Rect(cx, cy, card_w, card_h)
            card_rects.append((card_rect, key))

            # Hover
            hovered = card_rect.collidepoint(mx, my)
            bg = (60, 60, 60) if hovered else (30, 30, 30)
            border = info["color"]

            pygame.draw.rect(surf, bg, card_rect)
            pygame.draw.rect(surf, border, card_rect, 4 if hovered else 2)

            # Icon (big colored square)
            icon_size = 80
            icon_rect = pygame.Rect(cx + card_w // 2 - icon_size // 2, cy + 25, icon_size, icon_size)
            pygame.draw.rect(surf, info["icon_color"], icon_rect)
            pygame.draw.rect(surf, WHITE, icon_rect, 2)

            # Class name
            name_txt = title_font.render(info["name"], True, info["color"])
            surf.blit(name_txt, (cx + card_w // 2 - name_txt.get_width() // 2, cy + 120))

            # Description (word wrap)
            desc = info["desc"]
            words = desc.split(' ')
            lines = []
            current_line = ""
            for word in words:
                test = current_line + " " + word if current_line else word
                if desc_font.size(test)[0] < card_w - 30:
                    current_line = test
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            for j, line in enumerate(lines):
                line_txt = desc_font.render(line, True, LIGHT_GRAY)
                surf.blit(line_txt, (cx + card_w // 2 - line_txt.get_width() // 2, cy + 175 + j * 22))

            # Stats preview
            cls = PLAYER_CLASSES[key]
            stats = cls.BASE_STATS
            stat_y = cy + 250
            stat_items = [
                f"HP: {stats['max_health']}",
                f"DMG: {stats['damage']}",
                f"SPD: {stats['speed']}",
                f"RATE: {stats['fire_rate']}",
                f"PIERCE: {stats['piercing']}",
            ]
            for j, s in enumerate(stat_items):
                st = small_font.render(s, True, GRAY)
                surf.blit(st, (cx + 15, stat_y + j * 18))

        # Hint or waiting message
        if waiting_for_players:
            if net_mode == "host":
                ready_count = len(players_ready) + 1  # +1 for host
                total = len(players_ready) + 1 + (
                    len(net_host.clients) if net_host and hasattr(net_host, 'clients') else 0)
                hint = small_font.render(f"Waiting for players ({ready_count}/{total} ready)...", True, CYAN)
            else:
                hint = small_font.render("Waiting for all players to choose...", True, CYAN)
        else:
            hint = small_font.render("Click a class to begin", True, GRAY)
        surf.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))

        pygame.display.flip()

        # Check for class ready messages in multiplayer
        if net_mode == "host" and net_host and waiting_for_players:
            for msg in net_host.get_messages():
                if msg.get("type") == "class_ready":
                    pid = msg.get("player_id", -1)
                    players_ready.add(pid)
            # If all clients are ready, we can start
            client_count = len(net_host.clients) if hasattr(net_host, 'clients') else 0
            if len(players_ready) >= client_count:
                # Broadcast game start
                net_host.broadcast("all_classes_ready", {})
                return waiting_for_players  # Return the class we chose

        elif net_mode == "client" and net_client and waiting_for_players:
            for msg in net_client.get_messages():
                if msg.get("type") == "all_classes_ready":
                    # All players ready, start game
                    return waiting_for_players  # Return the class we chose

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and not waiting_for_players:
                for rect, key in card_rects:
                    if rect.collidepoint(event.pos):
                        # In multiplayer, broadcast our choice and wait
                        if net_mode in ("host", "client"):
                            waiting_for_players = key  # Store the chosen class
                            if net_mode == "host":
                                # Host: add self to ready, wait for clients
                                players_ready = set()
                            elif net_mode == "client":
                                # Client: tell host we're ready
                                net_client.send("class_ready", {"class": key})
                        else:
                            # Singleplayer: return immediately
                            return key

        clock.tick(30)


# ===========================================================
#                   MAIN MENU
# ===========================================================

def show_main_menu():
    clock = pygame.time.Clock()
    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BLACK)

        # Title
        title = header_font.render("Red's Garbage Game", True, RED)
        subtitle = title_font.render("Made With Love", True, DARK_GRAY)
        surf.blit(title, (sw // 2 - title.get_width() // 2, sh // 4 - 40))
        surf.blit(subtitle, (sw // 2 - subtitle.get_width() // 2, sh // 4 + 30))

        # Button layout
        btn_w = 260
        btn_h = 50
        btn_x = sw // 2 - btn_w // 2
        start_y = sh // 2 - 110

        # --- PLAY button ---
        play_btn = pygame.Rect(btn_x, start_y, btn_w, btn_h)
        c = GRAY if play_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, play_btn)
        pygame.draw.rect(surf, GREEN, play_btn, 3)
        txt = title_font.render("PLAY", True, GREEN)
        surf.blit(txt, (play_btn.centerx - txt.get_width() // 2, play_btn.centery - txt.get_height() // 2))

        # --- MULTIPLAYER button ---
        mp_btn = pygame.Rect(btn_x, start_y + 70, btn_w, btn_h)
        c = GRAY if mp_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, mp_btn)
        pygame.draw.rect(surf, CYAN, mp_btn, 3)
        txt = menu_font.render("MULTIPLAYER", True, CYAN)
        surf.blit(txt, (mp_btn.centerx - txt.get_width() // 2, mp_btn.centery - txt.get_height() // 2))

        # --- SETTINGS button ---
        settings_btn = pygame.Rect(btn_x, start_y + 140, btn_w, btn_h)
        c = GRAY if settings_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, settings_btn)
        pygame.draw.rect(surf, GOLD, settings_btn, 3)
        txt = menu_font.render("SETTINGS", True, GOLD)
        surf.blit(txt, (settings_btn.centerx - txt.get_width() // 2, settings_btn.centery - txt.get_height() // 2))

        # --- USERNAME button ---
        username_btn = pygame.Rect(btn_x, start_y + 210, btn_w, btn_h)
        c = GRAY if username_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, username_btn)
        pygame.draw.rect(surf, PINK, username_btn, 3)
        # Show the current username inside the button
        uname_label = small_font.render(f"NAME: {local_username}", True, PINK)
        surf.blit(uname_label, (username_btn.centerx - uname_label.get_width() // 2,
                                username_btn.centery - uname_label.get_height() // 2))

        # --- EXIT button ---
        exit_btn = pygame.Rect(btn_x, start_y + 280, btn_w, btn_h)
        c = GRAY if exit_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, exit_btn)
        pygame.draw.rect(surf, RED, exit_btn, 3)
        txt = menu_font.render("EXIT", True, RED)
        surf.blit(txt, (exit_btn.centerx - txt.get_width() // 2, exit_btn.centery - txt.get_height() // 2))

        # Controls hint
        hint = small_font.render("WASD / Arrow Keys to move  |  ESC for pause", True, GRAY)
        surf.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))

        pygame.display.flip()

        # --- EVENT HANDLING ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if play_btn.collidepoint(event.pos):
                    return "play"
                if mp_btn.collidepoint(event.pos):
                    return "multiplayer"
                if settings_btn.collidepoint(event.pos):
                    settings_menu.run(surf.copy())
                if username_btn.collidepoint(event.pos):
                    show_username_input()
                if exit_btn.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

        clock.tick(30)


# ===========================================================
#                   PAUSE MENU
# ===========================================================

def show_pause_menu():
    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        title = header_font.render("PAUSED", True, WHITE)
        surf.blit(title, (sw // 2 - title.get_width() // 2, sh // 4 - 20))

        btn_w, btn_h = 300, 45
        btn_x = sw // 2 - btn_w // 2
        start_y = sh // 2 - 50

        buttons = [
            ("Resume", GREEN, "resume"),
            ("Settings", GOLD, "settings"),
            ("Main Menu", ORANGE, "main_menu"),
            ("Exit Game", RED, "exit"),
        ]

        btn_rects = []
        for i, (label, color, action) in enumerate(buttons):
            r = pygame.Rect(btn_x, start_y + i * 60, btn_w, btn_h)
            c = GRAY if r.collidepoint(mx, my) else DARK_GRAY
            pygame.draw.rect(surf, c, r)
            pygame.draw.rect(surf, color, r, 2)
            txt = menu_font.render(label, True, color)
            surf.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
            btn_rects.append((r, action))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "resume"
            if event.type == pygame.MOUSEBUTTONDOWN:
                for r, action in btn_rects:
                    if r.collidepoint(event.pos):
                        if action == "settings":
                            settings_menu.run(surf.copy())
                        elif action == "exit":
                            pygame.quit();
                            sys.exit()
                        else:
                            return action

        clock.tick(30)


# ===========================================================
#                   GAME OVER SCREEN
# ===========================================================

def show_game_over(player_obj, wave):
    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BLACK)

        title = header_font.render("GAME OVER", True, RED)
        surf.blit(title, (sw // 2 - title.get_width() // 2, sh // 4 - 30))

        class_name = player_obj.DISPLAY_NAME
        stats = [
            f"Class: {class_name}",
            f"Reached Wave: {wave}",
            f"Level: {player_obj.level}",
            f"DMG: {player_obj.stats['damage']}  |  Pierce: {player_obj.stats['piercing']}  |  Multi: {player_obj.stats['multishot']}",
            f"Magnet: {player_obj.get_magnet_radius()}px",
        ]
        for i, s in enumerate(stats):
            txt = menu_font.render(s, True, LIGHT_GRAY)
            surf.blit(txt, (sw // 2 - txt.get_width() // 2, sh // 3 + 20 + i * 35))

        buttons = [
            ("Retry", GREEN, "restart"),
            ("Main Menu", ORANGE, "main_menu"),
            ("Exit Game", RED, "exit"),
        ]

        btn_w, btn_h = 250, 45
        btn_x = sw // 2 - btn_w // 2
        start_y = sh // 2 + 100

        btn_rects = []
        for i, (label, color, action) in enumerate(buttons):
            r = pygame.Rect(btn_x, start_y + i * 60, btn_w, btn_h)
            c = GRAY if r.collidepoint(mx, my) else DARK_GRAY
            pygame.draw.rect(surf, c, r)
            pygame.draw.rect(surf, color, r, 2)
            txt = menu_font.render(label, True, color)
            surf.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
            btn_rects.append((r, action))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for r, action in btn_rects:
                    if r.collidepoint(event.pos):
                        if action == "exit":
                            pygame.quit();
                            sys.exit()
                        return action

        clock.tick(30)


# ===========================================================
#                   GAME HELPERS
# ===========================================================

def get_nearest_enemies(player_obj, enemy_group, count):
    enemy_list = []
    for e in enemy_group:
        dist = math.hypot(e.rect.centerx - player_obj.rect.centerx,
                          e.rect.centery - player_obj.rect.centery)
        enemy_list.append((dist, e))
    enemy_list.sort(key=lambda x: x[0])
    return [e for _, e in enemy_list[:count]]


def handle_enemy_death(enemy_obj, all_spr, gem_grp, orb_grp, net_mode=None, net_host=None):
    xp_count = enemy_obj.get_xp_drop_count()
    gem_positions = []
    for i in range(xp_count):
        offset = (enemy_obj.rect.centerx + random.randint(-20, 20),
                  enemy_obj.rect.centery + random.randint(-20, 20))
        gem = ExpGem(offset)
        all_spr.add(gem)
        gem_grp.add(gem)
        gem_positions.append(offset)

    # Broadcast gem spawns to clients
    if net_mode == "host" and net_host and gem_positions:
        net_host.broadcast(MSG_GEM_SPAWN, {"positions": gem_positions})

    if random.random() < HEALTH_ORB_DROP_CHANCE:
        orb = HealthOrb(enemy_obj.rect.center)
        all_spr.add(orb)
        orb_grp.add(orb)
        # Broadcast orb spawn to clients
        if net_mode == "host" and net_host:
            net_host.broadcast(MSG_ORB_SPAWN, {
                "x": enemy_obj.rect.centerx,
                "y": enemy_obj.rect.centery,
                "heal": orb.heal_amount
            })


def apply_magnet(player_obj, gem_grp):
    """Pull nearby XP gems toward the player."""
    radius = player_obj.get_magnet_radius()
    if radius <= 0:
        return

    px, py = player_obj.rect.center
    for gem in gem_grp:
        dist = math.hypot(gem.rect.centerx - px, gem.rect.centery - py)
        if dist <= radius:
            pull_speed = max(3, 8 - (dist / radius) * 5)
            gem.move_toward((px, py), pull_speed)


# ===========================================================
#                   DRAWING FUNCTIONS
# ===========================================================

def draw_upgrade_counters(surf, player_obj):
    sx, sy = 10, 135
    header = font.render("Upgrades:", True, GOLD)
    surf.blit(header, (sx, sy - 22))

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
    ]

    for i, (label, key, value) in enumerate(stat_display):
        count = player_obj.upgrade_counts.get(key, 0)
        color = GOLD if count > 0 else GRAY
        text = small_font.render(f"{label}: {value}  (x{count})", True, color)
        surf.blit(text, (sx, sy + (i * 18)))


def draw_ui(surf, player_obj, wave, enemy_group, net_mode=None, party_level=None, party_xp=None, party_xp_to_next=None):
    sw = settings_module.SCREEN_WIDTH

    # XP Bar - Use party XP in multiplayer, local XP in singleplayer
    if net_mode in ("host", "client") and party_xp is not None:
        # Show party XP in multiplayer
        xp_to_next = max(1, party_xp_to_next)
        xp_ratio = party_xp / xp_to_next
        current_level = party_level
        current_xp_val = party_xp
    else:
        # Show local XP in singleplayer
        xp_to_next = max(1, player_obj.xp_to_next_level)
        xp_ratio = player_obj.current_xp / xp_to_next
        current_level = player_obj.level
        current_xp_val = player_obj.current_xp

    pygame.draw.rect(surf, DARK_GRAY, (0, 0, sw, 20))
    pygame.draw.rect(surf, BLUE, (0, 0, xp_ratio * sw, 20))
    xp_text = font.render(f"LVL {current_level}  ({current_xp_val}/{xp_to_next})", True, WHITE)
    surf.blit(xp_text, (10, 22))

    # Health Bar
    hp_bar_w, hp_bar_h = 200, 20
    hp_x, hp_y = 10, 48
    max_hp = max(1, player_obj.stats["max_health"])
    hp_ratio = max(0, player_obj.current_health / max_hp)
    pygame.draw.rect(surf, DARK_GRAY, (hp_x, hp_y, hp_bar_w, hp_bar_h))
    pygame.draw.rect(surf, RED, (hp_x, hp_y, hp_bar_w * hp_ratio, hp_bar_h))
    pygame.draw.rect(surf, WHITE, (hp_x, hp_y, hp_bar_w, hp_bar_h), 2)
    hp_str = f"{max(0, player_obj.current_health)} / {player_obj.stats['max_health']}"
    hp_text = font.render(hp_str, True, WHITE)
    surf.blit(hp_text, (hp_x + hp_bar_w // 2 - hp_text.get_width() // 2,
                        hp_y + hp_bar_h // 2 - hp_text.get_height() // 2))

    # Quick Stats
    quick = font.render(
        f"DMG:{player_obj.stats['damage']}  PIERCE:{player_obj.stats['piercing']}  "
        f"MULTI:{player_obj.stats['multishot']}  MAG:{player_obj.get_magnet_radius()}px",
        True, WHITE)
    surf.blit(quick, (10, 76))

    # Class name
    class_txt = small_font.render(f"Class: {player_obj.DISPLAY_NAME}", True, player_obj.SPRITE_COLOR)
    surf.blit(class_txt, (10, 98))

    # Wave Info
    wave_text = font.render(f"Wave: {wave}", True, WHITE)
    enemy_text = font.render(f"Enemies: {len(enemy_group)}", True, WHITE)
    surf.blit(wave_text, (sw - 150, 30))
    surf.blit(enemy_text, (sw - 150, 55))
    esc_text = small_font.render("[ESC] Pause", True, GRAY)
    surf.blit(esc_text, (sw - 150, 80))

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
            pygame.draw.rect(surf, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(surf, PURPLE, (bar_x, bar_y, bar_w * hp_ratio, bar_h))
            pygame.draw.rect(surf, WHITE, (bar_x, bar_y, bar_w, bar_h), 2)
            txt = boss_font.render("BOSS", True, WHITE)
            surf.blit(txt, (bar_x + bar_w // 2 - txt.get_width() // 2, bar_y - 35))


def draw_wave_banner(surf, wave):
    sw = settings_module.SCREEN_WIDTH
    sh = settings_module.SCREEN_HEIGHT
    if wave % 10 == 0:
        text = title_font.render(f"WAVE {wave} - BOSS!", True, PURPLE)
    else:
        text = title_font.render(f"WAVE {wave}", True, ORANGE)
    surf.blit(text, (sw // 2 - text.get_width() // 2, sh // 2 - 100))


def draw_enemy_health_bars(surf, enemy_group):
    for e in enemy_group:
        e.draw_health_bar(surf)


# ===========================================================
#                   UPGRADE MENU
# ===========================================================

def show_upgrade_menu(is_big, player_obj, all_spr, enemy_grp, net_mode=None, net_host=None, net_client=None):
    pool = BIG_UPGRADE_POOL if is_big else UPGRADE_POOL
    options = random.sample(pool, min(5, len(pool)))

    menu_active = True
    while menu_active:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()

        # Draw game underneath
        surf.fill(BLACK)
        all_spr.draw(surf)
        draw_enemy_health_bars(surf, enemy_grp)

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        if is_big:
            title = title_font.render("★ BIG UPGRADE! ★", True, GOLD)
        else:
            title = title_font.render("LEVEL UP!", True, YELLOW)
        surf.blit(title, (sw // 2 - title.get_width() // 2, 40))

        rects = []
        start_y = 100
        btn_spacing = 80
        mx, my = pygame.mouse.get_pos()

        for i, opt in enumerate(options):
            btn_rect = pygame.Rect(sw // 2 - 200, start_y + (i * btn_spacing), 400, 65)
            rects.append(btn_rect)

            btn_color = GRAY if btn_rect.collidepoint(mx, my) else DARK_GRAY
            border_color = GOLD if is_big else WHITE

            pygame.draw.rect(surf, btn_color, btn_rect)
            pygame.draw.rect(surf, border_color, btn_rect, 3)

            txt = font.render(opt["name"], True, GOLD if is_big else WHITE)
            surf.blit(txt, (btn_rect.centerx - txt.get_width() // 2, btn_rect.centery - 16))

            # Description + count
            base_key = opt["key"].replace("big_", "")
            count = player_obj.upgrade_counts.get(base_key, 0)
            desc_str = f'{opt.get("desc", "")}  |  Current: x{count}'
            dt = small_font.render(desc_str, True, LIGHT_GRAY)
            surf.blit(dt, (btn_rect.centerx - dt.get_width() // 2, btn_rect.centery + 8))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate(rects):
                    if rect.collidepoint(event.pos):
                        player_obj.apply_upgrade(options[i]["key"])
                        # Notify host/clients that we finished picking
                        if net_mode == "host" and net_host:
                            pass  # Host handles its own completion in the gem block
                        elif net_mode == "client" and net_client:
                            net_client.send(MSG_UPGRADE_DONE, {})
                        menu_active = False
                        break

        clock.tick(30)


# ===========================================================
#                   GAME SESSION
# ===========================================================

def run_game(class_key):
    global SCREEN_WIDTH, SCREEN_HEIGHT, upgrade_paused_by

    # Create player from selected class
    PlayerClass = PLAYER_CLASSES[class_key]
    player_obj = PlayerClass()
    player_obj.reposition(settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT)

    # Groups
    all_sprites = pygame.sprite.Group()
    enemies_grp = pygame.sprite.Group()
    bullets_grp = pygame.sprite.Group()
    gems_grp = pygame.sprite.Group()
    health_orbs_grp = pygame.sprite.Group()

    all_sprites.add(player_obj)

    # Wave state
    current_wave = 1
    enemies_to_spawn = 0
    enemies_spawned = 0
    spawn_timer = 0
    SPAWN_DELAY = 30
    wave_active = False
    wave_cooldown = 0
    WAVE_COOLDOWN_TIME = 120
    wave_banner_timer = 0
    fire_cooldown = 0

    # Party XP (shared in multiplayer, only tracked on host)
    party_level = 1
    party_xp = 0
    party_xp_to_next = 5
    upgrade_pending_players = set()  # Set of player IDs waiting to pick upgrades

    def start_wave(wave_num):
        nonlocal enemies_to_spawn, enemies_spawned, wave_active, spawn_timer, wave_banner_timer
        enemies_to_spawn = 5 + (wave_num * 2)
        enemies_spawned = 0
        wave_active = True
        spawn_timer = 0
        wave_banner_timer = 120
        if wave_num % 10 == 0:
            sounds.play_boss_spawn()
            trigger_shake(12, 8)
        else:
            sounds.play_wave_start()
        boss = None
        if wave_num % 10 == 0:
            boss = Boss(player_obj, wave_num)
            boss._net_id = id(boss)
            all_sprites.add(boss)
            enemies_grp.add(boss)
            # Broadcast boss spawn to clients
            if net_mode == "host" and net_host:
                net_host.broadcast(MSG_ENEMY_SPAWN, {
                    "enemy_id": boss._net_id,
                    "x": boss.rect.x,
                    "y": boss.rect.y,
                    "is_boss": True,
                    "wave": wave_num,
                    "max_health": boss.max_health,
                    "health": boss.health,
                })
        # Host broadcasts new wave to clients immediately
        if net_mode == "host" and net_host:
            net_host.broadcast(MSG_WAVE_START, {
                "wave": wave_num,
                "active": True,
                "enemies_remaining": enemies_to_spawn,
            })

    start_wave(current_wave)

    # Dash trail visual: list of (pos, alpha, frame) tuples
    dash_trail = []
    # Spectate state (multiplayer only)
    spectating = False
    spectate_target_id = None

    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()

        # ---- EVENTS ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if not spectating:
                        action = show_pause_menu()
                        if action == "main_menu":
                            return "main_menu"
                if event.key == pygame.K_SPACE and not spectating:
                    if player_obj.try_dash():
                        sounds.play_dash()
                        trigger_shake(3, 3)
                        # Seed the trail with current position
                        dash_trail.append([player_obj.rect.center, 200, 8])
                # Spectate: cycle through remote players with arrow keys
                if spectating and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    ids = list(remote_players.keys())
                    if ids:
                        if spectate_target_id not in ids:
                            spectate_target_id = ids[0]
                        else:
                            idx = ids.index(spectate_target_id)
                            if event.key == pygame.K_RIGHT:
                                spectate_target_id = ids[(idx + 1) % len(ids)]
                            else:
                                spectate_target_id = ids[(idx - 1) % len(ids)]

        # ---- WAVE SPAWNING ----
        # Clients don't spawn enemies autonomously — the host controls wave state
        # and broadcasts MSG_WAVE_START. Clients receive that and call start_wave().
        # PAUSE if anyone is choosing an upgrade
        if upgrade_paused_by:
            # DEBUG: Show we're paused
            if getattr(run_game, '_pause_debug_counter', 0) % 60 == 0:  # Print every second
                print(f"[{net_mode or 'SP'}] PAUSED: upgrade_paused_by = {upgrade_paused_by}")
            run_game._pause_debug_counter = getattr(run_game, '_pause_debug_counter', 0) + 1

        if not upgrade_paused_by:
            if net_mode != "client":
                if wave_active:
                    if enemies_spawned < enemies_to_spawn:
                        spawn_timer += 1
                        if spawn_timer >= SPAWN_DELAY:
                            spawn_timer = 0
                            e = Enemy(player_obj, current_wave)
                            e._net_id = id(e)  # Unique ID for network reporting
                            all_sprites.add(e)
                            enemies_grp.add(e)
                            enemies_spawned += 1
                            # Broadcast enemy spawn to clients
                            if net_mode == "host" and net_host:
                                net_host.broadcast(MSG_ENEMY_SPAWN, {
                                    "enemy_id": e._net_id,
                                    "x": e.rect.x,
                                    "y": e.rect.y,
                                    "is_boss": False,
                                    "wave": current_wave,
                                    "max_health": e.max_health,
                                    "health": e.health,
                                })
                    else:
                        if len(enemies_grp) == 0:
                            wave_active = False
                            wave_cooldown = WAVE_COOLDOWN_TIME
                            # Tell clients the wave is over
                            if net_mode == "host" and net_host:
                                net_host.broadcast(MSG_WAVE_COMPLETE, {"wave": current_wave})
                else:
                    wave_cooldown -= 1
                    if wave_cooldown <= 0:
                        current_wave += 1
                        start_wave(current_wave)
            # Client: just let existing enemies run; wave advancement comes from host

            # ---- UPDATE ----
            if spectating:
                # Only update non-player sprites (enemies, bullets, gems)
                enemies_grp.update()
                bullets_grp.update()
                gems_grp.update()
                health_orbs_grp.update()
            else:
                all_sprites.update()

            apply_magnet(player_obj, gems_grp)

            # ---- AUTO-FIRE ----
            if fire_cooldown <= 0 and not spectating:
                targets = get_nearest_enemies(player_obj, enemies_grp, player_obj.stats["multishot"])
                if targets:
                    weapon = player_obj.get_weapon_type()
                    for target in targets:
                        bsize = player_obj.stats.get("bullet_size", 1.0)
                        if weapon == "laser":
                            b = LaserBeam(player_obj.rect.center, target.rect.center,
                                          player_obj.stats["bullet_speed"], player_obj.stats["piercing"],
                                          size=bsize)
                        else:
                            b = Bullet(player_obj.rect.center, target.rect.center,
                                       player_obj.stats["bullet_speed"], player_obj.stats["piercing"],
                                       size=bsize)
                        all_sprites.add(b)
                        bullets_grp.add(b)

                        # Broadcast bullet to all other players
                        if net_mode in ("host", "client"):
                            bullet_data = {
                                "weapon": weapon,
                                "bx": player_obj.rect.centerx,
                                "by": player_obj.rect.centery,
                                "tx": target.rect.centerx,
                                "ty": target.rect.centery,
                                "speed": player_obj.stats["bullet_speed"],
                                "piercing": player_obj.stats["piercing"],
                                "damage": player_obj.stats["damage"],
                                "size": bsize,
                            }
                            if net_mode == "host" and net_host:
                                net_host.broadcast(MSG_BULLET_FIRE, bullet_data)
                            elif net_mode == "client" and net_client:
                                net_client.send(MSG_BULLET_FIRE, bullet_data)

                    fire_cooldown = player_obj.stats["fire_rate"]
                    if targets:
                        sounds.play_shoot()
            else:
                fire_cooldown -= 1

            # ---- COLLISIONS ----

            # Bullets/Lasers vs Enemies
            for bullet in list(bullets_grp):
                hit_list = pygame.sprite.spritecollide(bullet, enemies_grp, False)
                for enemy in hit_list:
                    if enemy in bullet.hit_enemies:
                        continue
                    bullet.hit_enemies.append(enemy)
                    # Use network damage if this bullet came from a remote player
                    dmg = getattr(bullet, '_net_damage', None) or player_obj.stats["damage"]
                    dead = enemy.take_damage(dmg)
                    bullet.hits += 1
                    if dead:
                        sounds.play_hit()
                        trigger_shake(4, 4)
                        # Report kill to host (clients) so host can sync gems/drops
                        if net_mode == "client" and net_client:
                            net_client.send(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                        elif net_mode == "host" and net_host:
                            # Host killed enemy directly — broadcast death
                            net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                        handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, net_mode, net_host)
                    if bullet.hits >= bullet.piercing:
                        bullet.kill()
                        break

            # Tank ram damage
            if hasattr(player_obj, 'ram_enemy') and player_obj.collision_damage > 0:
                ram_hits = pygame.sprite.spritecollide(player_obj, enemies_grp, False)
                for enemy in ram_hits:
                    dead = player_obj.ram_enemy(enemy)
                    if dead:
                        if net_mode == "client" and net_client:
                            net_client.send(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                        elif net_mode == "host" and net_host:
                            net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                    handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, net_mode, net_host)

            # Gems
            gem_hits = pygame.sprite.spritecollide(player_obj, gems_grp, True)
            for gem in gem_hits:
                sounds.play_gem()
                if net_mode in ("host", "client"):
                    # Multiplayer: report gem to host for party XP
                    if net_mode == "host":
                        party_xp += 1
                        # Check for party level up (host only)
                        if party_xp >= party_xp_to_next:
                            party_level += 1
                            party_xp = 0
                            party_xp_to_next = int(party_xp_to_next * 1.5)
                            is_big = party_level % 5 == 0
                            # Reset pending players set (host + all connected clients)
                            upgrade_pending_players = {0}  # Host is player 0
                            upgrade_pending_players.update(net_host.get_remote_states().keys())
                            # Broadcast party level up to everyone
                            net_host.broadcast(MSG_PARTY_LEVEL_UP, {
                                "level": party_level,
                                "is_big": is_big,
                            })
                            sounds.play_level_up()
                            # Host opens own upgrade menu
                            show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, net_mode, net_host,
                                              net_client)
                            # Remove self from pending set
                            upgrade_pending_players.discard(0)
                            # If no other players, resume immediately
                            if not upgrade_pending_players:
                                net_host.broadcast(MSG_UPGRADE_RESUME, {})
                            else:
                                net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name": "Party", "level": party_level})
                    elif net_mode == "client":
                        # Send gem pickup to host
                        net_client.send(MSG_GEM_COLLECT, {})
                else:
                    # Singleplayer: local XP
                    player_obj.current_xp += 1
                    if player_obj.current_xp >= player_obj.xp_to_next_level:
                        player_obj.level += 1
                        player_obj.current_xp = 0
                        player_obj.xp_to_next_level = int(player_obj.xp_to_next_level * 1.5)
                        sounds.play_level_up()
                        if player_obj.level % 5 == 0:
                            show_upgrade_menu(True, player_obj, all_sprites, enemies_grp, net_mode, net_host,
                                              net_client)
                        else:
                            show_upgrade_menu(False, player_obj, all_sprites, enemies_grp, net_mode, net_host,
                                              net_client)

            # Health Orbs
            orb_hits = pygame.sprite.spritecollide(player_obj, health_orbs_grp, True)
            for orb in orb_hits:
                player_obj.heal(orb.heal_amount)

            # Enemies hit Player
            hit_enemies = pygame.sprite.spritecollide(player_obj, enemies_grp, False)
            if hit_enemies and not spectating and not player_obj.dash_invincible:
                now = pygame.time.get_ticks()
                if now - player_obj.last_hit > 1000:
                    worst_damage = max(e.damage for e in hit_enemies)
                    player_obj.current_health -= worst_damage
                    player_obj.last_hit = now
                    player_obj.set_hurt(True)
                    sounds.play_hurt()
                    trigger_shake(8, 6)
                    if player_obj.current_health <= 0:
                        sounds.play_death()
                        if net_mode in ("host", "client") and remote_players:
                            # Enter spectate mode instead of game over
                            spectating = True
                            spectate_target_id = next(iter(remote_players))
                            player_obj.kill()  # Remove from sprite groups
                        else:
                            result = show_game_over(player_obj, current_wave)
                            return result
                else:
                    flicker = (now // 100) % 2 == 0
                    player_obj.set_hurt(flicker)
            elif not hit_enemies and not spectating:
                player_obj.set_hurt(False)

        # ---- DRAW ----
        surf.fill(BLACK)

        # Screen shake offset
        global _shake_frames, _shake_intensity
        shake_x, shake_y = 0, 0
        if _shake_frames > 0:
            shake_x = random.randint(-_shake_intensity, _shake_intensity)
            shake_y = random.randint(-_shake_intensity, _shake_intensity)
            _shake_frames -= 1
            if _shake_frames == 0:
                _shake_intensity = 0

        # We blit everything to a temp surface then offset it
        shake_surf = pygame.Surface((sw, sh))
        shake_surf.fill(BLACK)

        # Magnet ring (behind sprites)
        if not spectating:
            player_obj.draw_magnet_ring(shake_surf)

        # Tank ram aura
        if not spectating and hasattr(player_obj, 'draw_ram_aura'):
            player_obj.draw_ram_aura(shake_surf)

        # Dash trail
        if player_obj.dash_duration > 0 or dash_trail:
            dash_trail.append([player_obj.rect.center, 180, 6])
        new_trail = []
        for trail_entry in dash_trail:
            pos, alpha, radius = trail_entry
            if alpha > 0:
                ts = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(ts, (100, 200, 255, alpha), (radius, radius), radius)
                shake_surf.blit(ts, (pos[0] - radius, pos[1] - radius))
                trail_entry[1] = max(0, alpha - 30)
                trail_entry[2] = max(1, radius - 1)
                new_trail.append(trail_entry)
        dash_trail[:] = new_trail

        all_sprites.draw(shake_surf)
        draw_enemy_health_bars(shake_surf, enemies_grp)

        # ========== NETWORKING ==========
        net_send_timer = getattr(run_game, '_net_timer', 0)

        if net_mode == "host" and net_host:
            net_send_timer += 1
            if net_send_timer >= 3:
                net_send_timer = 0
                net_host.broadcast(MSG_PLAYER_STATE, {
                    "player_id": 0,
                    "x": player_obj.rect.x,
                    "y": player_obj.rect.y,
                    "health": player_obj.current_health,
                    "class": player_obj.CLASS_KEY,
                    "level": player_obj.level,
                    "username": local_username,
                })

            # Broadcast enemy positions every 5 frames (15fps sync)
            enemy_timer = getattr(run_game, '_enemy_timer', 0)
            enemy_timer += 1
            if enemy_timer >= 5:
                enemy_timer = 0
                enemy_states = []
                for e in enemies_grp:
                    enemy_states.append({
                        "enemy_id": getattr(e, '_net_id', id(e)),
                        "x": e.rect.x,
                        "y": e.rect.y,
                        "health": e.health,
                        "max_health": e.max_health,
                    })
                if enemy_states:
                    net_host.broadcast(MSG_ENEMY_UPDATE, {"enemies": enemy_states})
            run_game._enemy_timer = enemy_timer

            for msg in net_host.get_messages():
                msg_type = msg.get("type", "")
                data = msg.get("data", {})
                from_id = msg.get("_from", -1)

                if msg_type == MSG_BULLET_FIRE:
                    # Spawn remote bullet locally on host screen
                    btype = data.get("weapon", "bullet")
                    bpos = (data.get("bx", 0), data.get("by", 0))
                    tpos = (data.get("tx", 0), data.get("ty", 0))
                    bspd = data.get("speed", 7)
                    bprc = data.get("piercing", 1)
                    bdmg = data.get("damage", 1)
                    bsz = data.get("size", 1.0)
                    if btype == "laser":
                        rb = LaserBeam(bpos, tpos, bspd, bprc, size=bsz)
                    else:
                        rb = Bullet(bpos, tpos, bspd, bprc, size=bsz)
                    rb._net_damage = bdmg
                    all_sprites.add(rb)
                    bullets_grp.add(rb)

                elif msg_type == MSG_ENEMY_DEAD:
                    # Client reported killing an enemy — find and kill it by net_id
                    eid = data.get("enemy_id", -1)
                    for e in list(enemies_grp):
                        if getattr(e, '_net_id', None) == eid:
                            handle_enemy_death(e, all_sprites, gems_grp, health_orbs_grp, net_mode, net_host)
                            e.kill()
                            # Broadcast death to all clients so they remove their ghost
                            net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": eid})
                            break

                elif msg_type == MSG_GEM_COLLECT:
                    # Client picked up a gem — add to party XP
                    party_xp += 1
                    if party_xp >= party_xp_to_next:
                        party_level += 1
                        party_xp = 0
                        party_xp_to_next = int(party_xp_to_next * 1.5)
                        is_big = party_level % 5 == 0
                        # Reset pending players (host + all clients)
                        upgrade_pending_players = {0}
                        upgrade_pending_players.update(net_host.get_remote_states().keys())
                        # Broadcast level up
                        net_host.broadcast(MSG_PARTY_LEVEL_UP, {
                            "level": party_level,
                            "is_big": is_big,
                        })
                        sounds.play_level_up()
                        # Host opens own upgrade menu
                        show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, net_mode, net_host, net_client)
                        # Remove self from pending
                        upgrade_pending_players.discard(0)
                        # If no other players, resume immediately
                        if not upgrade_pending_players:
                            upgrade_paused_by = None
                            net_host.broadcast(MSG_UPGRADE_RESUME, {})
                        else:
                            upgrade_paused_by = {"player_name": "Party", "level": party_level}
                            net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name": "Party", "level": party_level})

                elif msg_type == MSG_UPGRADE_DONE:
                    # Client finished picking upgrade
                    upgrade_pending_players.discard(from_id)
                    if not upgrade_pending_players:
                        # Everyone done — resume game
                        upgrade_paused_by = None
                        net_host.broadcast(MSG_UPGRADE_RESUME, {})

            # --- Host: update & broadcast remote player ghosts ---
            usernames = net_host.get_usernames()
            for pid, state in net_host.get_remote_states().items():
                if pid not in remote_players:
                    uname = usernames.get(pid, f"Player{pid}")
                    ghost = RemotePlayerGhost(pid, state.get("class", "default"), username=uname)
                    remote_players[pid] = ghost
                else:
                    uname = usernames.get(pid, remote_players[pid].username)
                    remote_players[pid].username = uname
                remote_players[pid].update_from_state(state)
                remote_players[pid].update()

            # --- Host-authoritative wave broadcasting ---
            # Broadcast current wave state every second so clients stay in sync
            wave_bcast_timer = getattr(run_game, '_wave_bcast', 0) + 1
            run_game._wave_bcast = wave_bcast_timer
            if wave_bcast_timer % 60 == 0:
                net_host.broadcast(MSG_WAVE_START, {
                    "wave": current_wave,
                    "active": wave_active,
                    "enemies_remaining": len(enemies_grp),
                    "party_level": party_level,
                    "party_xp": party_xp,
                    "party_xp_to_next": party_xp_to_next,
                })

        elif net_mode == "client" and net_client:
            net_send_timer += 1
            if net_send_timer >= 3:
                net_send_timer = 0
                net_client.send_player_state(
                    player_obj.rect.x, player_obj.rect.y,
                    player_obj.current_health, player_obj.CLASS_KEY,
                    player_obj.level
                )

            for msg in net_client.get_messages():
                msg_type = msg.get("type", "")
                data = msg.get("data", {})

                if msg_type == MSG_PLAYER_STATE:
                    pid = data.get("player_id", -1)
                    if pid not in remote_players:
                        uname = data.get("username", f"Player{pid}")
                        ghost = RemotePlayerGhost(pid, data.get("class", "default"), username=uname)
                        remote_players[pid] = ghost
                    remote_players[pid].update_from_state(data)
                    remote_players[pid].update()

                elif msg_type == MSG_USERNAME:
                    pid = data.get("player_id", -1)
                    uname = data.get("username", f"Player{pid}")
                    if pid in remote_players:
                        remote_players[pid].username = uname

                elif msg_type == MSG_BULLET_FIRE:
                    # Spawn remote bullet locally on client screen
                    btype = data.get("weapon", "bullet")
                    bpos = (data.get("bx", 0), data.get("by", 0))
                    tpos = (data.get("tx", 0), data.get("ty", 0))
                    bspd = data.get("speed", 7)
                    bprc = data.get("piercing", 1)
                    bdmg = data.get("damage", 1)
                    bsz = data.get("size", 1.0)
                    if btype == "laser":
                        rb = LaserBeam(bpos, tpos, bspd, bprc, size=bsz)
                    else:
                        rb = Bullet(bpos, tpos, bspd, bprc, size=bsz)
                    rb._net_damage = bdmg
                    all_sprites.add(rb)
                    bullets_grp.add(rb)

                elif msg_type == MSG_ENEMY_SPAWN:
                    # Host spawned an enemy — create a ghost
                    eid = data.get("enemy_id")
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    is_boss = data.get("is_boss", False)
                    wave = data.get("wave", 1)
                    max_hp = data.get("max_health", 1)
                    hp = data.get("health", 1)
                    ghost = RemoteEnemyGhost(eid, x, y, is_boss, wave)
                    ghost.max_health = max_hp
                    ghost.health = hp
                    remote_enemies[eid] = ghost
                    all_sprites.add(ghost)
                    enemies_grp.add(ghost)

                elif msg_type == MSG_ENEMY_UPDATE:
                    # Host sent enemy position updates
                    enemy_list = data.get("enemies", [])
                    for edata in enemy_list:
                        eid = edata.get("enemy_id")
                        if eid in remote_enemies:
                            remote_enemies[eid].update_from_state(edata)

                elif msg_type == MSG_ENEMY_DEAD:
                    # Host says enemy died — remove ghost
                    eid = data.get("enemy_id")
                    if eid in remote_enemies:
                        remote_enemies[eid].kill()
                        del remote_enemies[eid]

                elif msg_type == MSG_GEM_SPAWN:
                    # Host spawned gems — create them locally
                    positions = data.get("positions", [])
                    for pos in positions:
                        gem = ExpGem(pos)
                        all_sprites.add(gem)
                        gems_grp.add(gem)

                elif msg_type == MSG_ORB_SPAWN:
                    # Host spawned health orb — create it locally
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    heal = data.get("heal", 20)
                    orb = HealthOrb((x, y))
                    orb.heal_amount = heal
                    all_sprites.add(orb)
                    health_orbs_grp.add(orb)

                elif msg_type == MSG_PARTY_LEVEL_UP:
                    # Party leveled up — open upgrade menu
                    # Update party XP variables (nonlocal to update run_game scope)
                    party_level = data.get("level", 1)
                    party_xp = 0  # Reset after level up
                    party_xp_to_next = int(party_xp_to_next * 1.5)  # Increase threshold
                    is_big = data.get("is_big", False)
                    sounds.play_level_up()
                    show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, net_mode, net_host, net_client)

                elif msg_type == MSG_UPGRADE_PAUSE:
                    # Upgrade pause (party is choosing)
                    print(f"[Client] Received MSG_UPGRADE_PAUSE: {data}")  # DEBUG
                    upgrade_paused_by = {
                        "player_name": data.get("player_name", "Party"),
                        "level": data.get("level", 1)
                    }
                    print(f"[Client] Set upgrade_paused_by = {upgrade_paused_by}")  # DEBUG

                elif msg_type == MSG_UPGRADE_RESUME:
                    # All players finished choosing
                    print(f"[Client] Received MSG_UPGRADE_RESUME")  # DEBUG
                    upgrade_paused_by = None
                    print(f"[Client] Cleared upgrade_paused_by")  # DEBUG

                elif msg_type == MSG_WAVE_START:
                    # Host told us which wave we're on + party XP state
                    srv_wave = data.get("wave", current_wave)

                    # Update party XP from host
                    if "party_level" in data:
                        party_level = data["party_level"]
                    if "party_xp" in data:
                        party_xp = data["party_xp"]
                    if "party_xp_to_next" in data:
                        party_xp_to_next = data["party_xp_to_next"]

                    if srv_wave != current_wave:
                        # Advance to the host's wave
                        current_wave = srv_wave
                        # Clear existing enemies so we don't double-spawn
                        for e in list(enemies_grp):
                            e.kill()
                        remote_enemies.clear()
                        start_wave(current_wave)

                elif msg_type == MSG_WAVE_COMPLETE:
                    # Host says wave is done
                    wave_active = False
                    wave_cooldown = WAVE_COOLDOWN_TIME

            # --- Client: suppress autonomous wave spawning ---
            # Clients don't spawn enemies independently; they rely on the host's
            # MSG_WAVE_START messages to stay in sync. So we skip the spawning
            # logic block above when in client mode. We still allow enemies that
            # exist locally to update & be killed by local bullets (damage is
            # applied locally and reported back to host via MSG_ENEMY_DEAD).
            # Reset wave_active so client loop doesn't advance waves on its own.
            # (Handled by not re-running the wave spawning block — see comment
            # below the wave spawning section.)

            if not net_client.connected:
                pass

        run_game._net_timer = net_send_timer

        # ========== BLIT GAME WORLD WITH SHAKE OFFSET ==========
        surf.blit(shake_surf, (shake_x, shake_y))

        # ========== DRAW REMOTE PLAYERS ==========
        for pid, ghost in remote_players.items():
            surf.blit(ghost.image, ghost.rect)
            ghost.draw_label(surf)

        # ========== UPGRADE PAUSE OVERLAY ==========
        if upgrade_paused_by and not spectating:
            # Semi-transparent overlay
            pause_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 150))
            surf.blit(pause_overlay, (0, 0))

            # Message
            pname = upgrade_paused_by.get("player_name", "Player")
            plevel = upgrade_paused_by.get("level", 1)
            wait_txt = title_font.render(f"{pname} is choosing upgrade...", True, GOLD)
            surf.blit(wait_txt, (sw // 2 - wait_txt.get_width() // 2, sh // 2 - 80))
            lvl_txt = small_font.render(f"Level {plevel}", True, GRAY)
            surf.blit(lvl_txt, (sw // 2 - lvl_txt.get_width() // 2, sh // 2 - 30))

            # Debug indicator showing game is paused
            paused_txt = title_font.render("GAME PAUSED", True, RED)
            surf.blit(paused_txt, (sw // 2 - paused_txt.get_width() // 2, sh // 2 + 20))

        # ========== SPECTATE OVERLAY ==========
        if spectating:
            # Dark vignette
            spec_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            spec_overlay.fill((0, 0, 0, 120))
            surf.blit(spec_overlay, (0, 0))

            # Follow camera label (we can't truly move the camera but highlight who we're watching)
            if spectate_target_id and spectate_target_id in remote_players:
                ghost = remote_players[spectate_target_id]
                # Draw a bright ring around spectated player
                pygame.draw.circle(surf, CYAN, ghost.rect.center, ghost.rect.width + 8, 2)
                name_surf = menu_font.render(f"Watching: {ghost.username}", True, CYAN)
                surf.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, 50))

            dead_txt = title_font.render("YOU DIED", True, RED)
            surf.blit(dead_txt, (sw // 2 - dead_txt.get_width() // 2, sh // 2 - 60))
            spec_hint = small_font.render("Spectating  |  ← → to switch player", True, LIGHT_GRAY)
            surf.blit(spec_hint, (sw // 2 - spec_hint.get_width() // 2, sh // 2 - 20))
            wave_txt = small_font.render(f"Wave {current_wave}  |  {len(enemies_grp)} enemies remaining", True, GRAY)
            surf.blit(wave_txt, (sw // 2 - wave_txt.get_width() // 2, sh // 2 + 10))
        else:
            # ========== DRAW UI ==========
            draw_ui(surf, player_obj, current_wave, enemies_grp, net_mode, party_level, party_xp, party_xp_to_next)
            draw_boss_health_bar(surf, enemies_grp)

            # Dash cooldown bar (bottom-centre)
            dash_ratio = player_obj.get_dash_cooldown_ratio()
            bar_w, bar_h = 120, 8
            bar_x = sw // 2 - bar_w // 2
            bar_y = sh - 20
            pygame.draw.rect(surf, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
            ready_w = int(bar_w * (1.0 - dash_ratio))
            bar_color = CYAN if dash_ratio == 0 else STEEL_BLUE
            pygame.draw.rect(surf, bar_color, (bar_x, bar_y, ready_w, bar_h))
            pygame.draw.rect(surf, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)
            dash_label = small_font.render("DASH [SPACE]" if dash_ratio == 0 else "DASH", True,
                                           CYAN if dash_ratio == 0 else GRAY)
            surf.blit(dash_label, (bar_x + bar_w // 2 - dash_label.get_width() // 2, bar_y - 16))

        if wave_banner_timer > 0:
            draw_wave_banner(surf, current_wave)
            wave_banner_timer -= 1

        # ========== DRAW NETWORK INFO ==========
        if net_mode:
            if net_mode == "host":
                count = net_host.get_player_count() if net_host else 1
                net_txt = small_font.render(f"Hosting | {count} players", True, CYAN)
            else:
                status = "Connected" if (net_client and net_client.connected) else "Disconnected"
                color = GREEN if status == "Connected" else RED
                net_txt = small_font.render(f"Client | {status}", True, color)
            surf.blit(net_txt, (sw - 200, 105))

        pygame.display.flip()
        clock.tick(FPS)

    return "main_menu"


class RemoteEnemyGhost(pygame.sprite.Sprite):
    """Client-side mirror of a host's enemy. No AI, just visual tracking."""

    def __init__(self, enemy_id, x, y, is_boss=False, wave=1):
        super().__init__()
        self.enemy_id = enemy_id
        self.is_boss = is_boss
        self.target_x = x
        self.target_y = y
        self.max_health = 1
        self.health = 1
        self.damage = 25 if is_boss else 10

        size = (50, 50) if is_boss else (30, 30)
        color = PURPLE if is_boss else RED
        fname = "boss.png" if is_boss else "enemy_basic.png"
        self.image = load_sprite(fname, size, color, size)
        self.image.set_alpha(200)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update_from_state(self, state):
        self.target_x = state.get("x", self.target_x)
        self.target_y = state.get("y", self.target_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get("max_health", self.max_health)

    def update(self):
        # Smooth interpolation to reduce jitter
        self.rect.x += (self.target_x - self.rect.x) * 0.4
        self.rect.y += (self.target_y - self.rect.y) * 0.4

    def take_damage(self, amount):
        """Mirror method — doesn't actually do damage calc, just for interface compatibility."""
        pass

    def draw_health_bar(self, surf):
        """Draw health bar above enemy ghost."""
        if self.health >= self.max_health:
            return

        bar_width = self.rect.width
        bar_height = 5
        bar_x = self.rect.x
        bar_y = self.rect.y - 8

        hp_ratio = max(0, self.health / max(1, self.max_health))

        if hp_ratio > 0.5:
            color = GREEN
        elif hp_ratio > 0.25:
            color = YELLOW
        else:
            color = RED

        pygame.draw.rect(surf, DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(surf, color, (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(surf, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)


class RemotePlayerGhost(pygame.sprite.Sprite):
    """Visual representation of another player in multiplayer."""

    def __init__(self, player_id, class_key="default", username=None):
        super().__init__()
        info = CLASS_INFO.get(class_key, CLASS_INFO["default"])
        self.player_id = player_id
        self.class_key = class_key
        self.username = username or f"Player{player_id}"
        self.target_x = 0
        self.target_y = 0
        self.level = 1
        self.health = 100

        # Use class sprite with transparency
        sprite_map = {
            "default": ("player_default.png", (40, 40), GREEN),
            "tank": ("player_tank.png", (50, 50), STEEL_BLUE),
            "laser": ("player_laser.png", (40, 40), LASER_RED),
        }
        fname, size, color = sprite_map.get(class_key, sprite_map["default"])
        self.image = load_sprite(fname, size, color, size)
        self.image.set_alpha(180)  # Slightly transparent
        self.rect = self.image.get_rect()

    def update_from_state(self, state):
        self.target_x = state.get("x", self.target_x)
        self.target_y = state.get("y", self.target_y)
        self.health = state.get("health", self.health)
        self.level = state.get("level", self.level)
        # Update username if carried in state
        if "username" in state:
            self.username = state["username"]

        new_class = state.get("class", self.class_key)
        if new_class != self.class_key:
            self.class_key = new_class
            sprite_map = {
                "default": ("player_default.png", (40, 40), GREEN),
                "tank": ("player_tank.png", (50, 50), STEEL_BLUE),
                "laser": ("player_laser.png", (40, 40), LASER_RED),
            }
            fname, size, color = sprite_map.get(new_class, sprite_map["default"])
            self.image = load_sprite(fname, size, color, size)
            self.image.set_alpha(180)
            self.rect = self.image.get_rect()

    def update(self):
        # Smooth interpolation
        self.rect.x += (self.target_x - self.rect.x) * 0.3
        self.rect.y += (self.target_y - self.rect.y) * 0.3

    def draw_label(self, surf):
        label = small_font.render(f"{self.username} Lv{self.level}", True, CYAN)
        surf.blit(label, (self.rect.centerx - label.get_width() // 2, self.rect.y - 18))


# ===========================================================
#                   USERNAME INPUT SCREEN
# ===========================================================

def _save_username(name):
    """Persist username into config.json."""
    settings_module.config["username"] = name
    settings_module.save_config(settings_module.config)


def show_username_input():
    """Ask the player to enter a username before entering multiplayer. Returns the username string."""
    global local_username
    username = local_username  # Pre-fill with current value
    input_active = True
    MAX_LEN = 16

    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BLACK)

        title = header_font.render("ENTER USERNAME", True, CYAN)
        surf.blit(title, (sw // 2 - title.get_width() // 2, sh // 4 - 30))

        hint = small_font.render("Your name will be shown above your character.", True, GRAY)
        surf.blit(hint, (sw // 2 - hint.get_width() // 2, sh // 4 + 35))

        # Input box
        box_w, box_h = 400, 55
        box_x = sw // 2 - box_w // 2
        box_y = sh // 2 - box_h // 2 - 20
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(surf, DARK_GRAY, box_rect)
        pygame.draw.rect(surf, GOLD, box_rect, 3)

        display_text = username + ("|" if (pygame.time.get_ticks() // 500) % 2 == 0 else "")
        name_txt = title_font.render(display_text, True, WHITE)
        surf.blit(name_txt, (box_x + 15, box_y + box_h // 2 - name_txt.get_height() // 2))

        char_count = small_font.render(f"{len(username)}/{MAX_LEN}", True, GRAY)
        surf.blit(char_count, (box_x + box_w - char_count.get_width() - 8, box_y + box_h + 6))

        # Confirm button
        btn_w, btn_h = 200, 45
        btn_x = sw // 2 - btn_w // 2
        btn_y = sh // 2 + 60
        confirm_btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        can_confirm = len(username.strip()) > 0
        btn_color = GRAY if (can_confirm and confirm_btn.collidepoint(mx, my)) else DARK_GRAY
        border_color = GREEN if can_confirm else DARK_GRAY
        pygame.draw.rect(surf, btn_color, confirm_btn)
        pygame.draw.rect(surf, border_color, confirm_btn, 3)
        btn_txt = menu_font.render("Confirm", True, GREEN if can_confirm else GRAY)
        surf.blit(btn_txt, (confirm_btn.centerx - btn_txt.get_width() // 2,
                            confirm_btn.centery - btn_txt.get_height() // 2))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if username.strip():
                        local_username = username.strip()
                        _save_username(local_username)
                        return local_username
                elif event.key == pygame.K_BACKSPACE:
                    username = username[:-1]
                elif event.key == pygame.K_ESCAPE:
                    if not username.strip():
                        username = "Player"
                    local_username = username.strip()
                    _save_username(local_username)
                    return local_username
                elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    # Paste from clipboard
                    try:
                        if not pygame.scrap.get_init():
                            pygame.scrap.init()
                        clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if clip:
                            text = clip.decode("utf-8", errors="ignore").replace("\x00", "").strip()
                            remaining = MAX_LEN - len(username)
                            username += text[:remaining]
                    except Exception:
                        pass
                else:
                    if len(username) < MAX_LEN and event.unicode.isprintable():
                        username += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN:
                if confirm_btn.collidepoint(event.pos) and username.strip():
                    local_username = username.strip()
                    _save_username(local_username)
                    return local_username

        clock.tick(60)


# ===========================================================
#                   MULTIPLAYER MENU
# ===========================================================

def show_multiplayer_menu():
    """Menu to choose host/join/singleplayer."""
    global net_host, net_client, net_mode

    ip_input = ""
    input_active = False
    status_msg = ""
    status_color = WHITE

    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BLACK)

        title = header_font.render(GAME_NAME, True, RED)
        surf.blit(title, (sw // 2 - title.get_width() // 2, 40))

        ver = small_font.render(f"v{VERSION}", True, GRAY)
        surf.blit(ver, (sw // 2 - ver.get_width() // 2, 95))

        subtitle = title_font.render("Online", True, GOLD)
        surf.blit(subtitle, (sw // 2 - subtitle.get_width() // 2, 130))

        btn_w, btn_h = 350, 50
        btn_x = sw // 2 - btn_w // 2
        start_y = 200

        # Singleplayer button
        sp_btn = pygame.Rect(btn_x, start_y, btn_w, btn_h)
        c = GRAY if sp_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, sp_btn)
        pygame.draw.rect(surf, GREEN, sp_btn, 3)
        txt = menu_font.render("Singleplayer", True, GREEN)
        surf.blit(txt, (sp_btn.centerx - txt.get_width() // 2, sp_btn.centery - txt.get_height() // 2))

        # Host button
        host_btn = pygame.Rect(btn_x, start_y + 70, btn_w, btn_h)
        c = GRAY if host_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, host_btn)
        pygame.draw.rect(surf, CYAN, host_btn, 3)
        local_ip = get_local_ip()
        txt = menu_font.render("Host Game", True, CYAN)
        surf.blit(txt, (host_btn.centerx - txt.get_width() // 2, host_btn.centery - txt.get_height() // 2 - 8))
        ip_sub = small_font.render(f"Your IP: {local_ip}", True, CYAN)
        surf.blit(ip_sub, (host_btn.centerx - ip_sub.get_width() // 2, host_btn.centery + 10))

        # Join section
        join_label = menu_font.render("Join by IP:", True, ORANGE)
        surf.blit(join_label, (btn_x, start_y + 150))

        ip_box = pygame.Rect(btn_x, start_y + 180, btn_w - 110, 40)
        box_color = GOLD if input_active else WHITE
        pygame.draw.rect(surf, DARK_GRAY, ip_box)
        pygame.draw.rect(surf, box_color, ip_box, 2)
        ip_txt = menu_font.render(ip_input + ("|" if input_active else ""), True, WHITE)
        surf.blit(ip_txt, (ip_box.x + 10, ip_box.centery - ip_txt.get_height() // 2))

        join_btn = pygame.Rect(btn_x + btn_w - 100, start_y + 180, 100, 40)
        c = GRAY if join_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, join_btn)
        pygame.draw.rect(surf, ORANGE, join_btn, 2)
        txt = menu_font.render("Join", True, ORANGE)
        surf.blit(txt, (join_btn.centerx - txt.get_width() // 2, join_btn.centery - txt.get_height() // 2))

        # Back button
        back_btn = pygame.Rect(btn_x, start_y + 280, btn_w, 40)
        c = GRAY if back_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, back_btn)
        pygame.draw.rect(surf, WHITE, back_btn, 2)
        txt = menu_font.render("Back to Main Menu", True, WHITE)
        surf.blit(txt, (back_btn.centerx - txt.get_width() // 2, back_btn.centery - txt.get_height() // 2))

        # Status message
        if status_msg:
            st = menu_font.render(status_msg, True, status_color)
            surf.blit(st, (sw // 2 - st.get_width() // 2, start_y + 240))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None, None
                if input_active:
                    if event.key == pygame.K_RETURN:
                        # Try to join
                        ip = ip_input.strip()
                        if ip:
                            status_msg = f"Connecting to {ip}..."
                            status_color = YELLOW
                            pygame.display.flip()
                            net_client = GameClient()
                            if net_client.connect(ip):
                                net_mode = "client"
                                net_client.send_username(local_username)
                                return "client", net_client
                            else:
                                status_msg = "Connection failed!"
                                status_color = RED
                                net_client = None
                    elif event.key == pygame.K_BACKSPACE:
                        ip_input = ip_input[:-1]
                    elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        # Paste from clipboard
                        try:
                            if not pygame.scrap.get_init():
                                pygame.scrap.init()
                            clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                            if clip:
                                text = clip.decode("utf-8", errors="ignore").replace("\x00", "").strip()
                                remaining = 21 - len(ip_input)
                                ip_input += text[:remaining]
                        except Exception:
                            pass
                    else:
                        if len(ip_input) < 21:
                            ip_input += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN:
                input_active = ip_box.collidepoint(event.pos)

                if sp_btn.collidepoint(event.pos):
                    net_mode = None
                    return "singleplayer", None

                if host_btn.collidepoint(event.pos):
                    net_host = GameHost()
                    ip = net_host.start()
                    net_mode = "host"
                    status_msg = f"Hosting on {ip}:{DEFAULT_PORT} - waiting for players..."
                    status_color = GREEN
                    return "host", net_host

                if join_btn.collidepoint(event.pos):
                    ip = ip_input.strip()
                    if ip:
                        status_msg = f"Connecting to {ip}..."
                        status_color = YELLOW
                        pygame.display.flip()
                        net_client = GameClient()
                        if net_client.connect(ip):
                            net_mode = "client"
                            net_client.send_username(local_username)
                            return "client", net_client
                        else:
                            status_msg = "Connection failed!"
                            status_color = RED
                            net_client = None

                if back_btn.collidepoint(event.pos):
                    return None, None

        clock.tick(30)


# LOBBIES

def show_lobby():
    """Multiplayer lobby — wait for players, then start."""
    global net_host, net_client, net_mode
    clock_lobby = pygame.time.Clock()

    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "Unknown"

    while True:
        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BLACK)

        # Title
        title = header_font.render("LOBBY", True, CYAN)
        surf.blit(title, (sw // 2 - title.get_width() // 2, 40))

        if net_mode == "host":
            info = menu_font.render("You are the HOST", True, GREEN)
            surf.blit(info, (sw // 2 - info.get_width() // 2, 110))

            ip_text = menu_font.render(f"Your IP: {local_ip}", True, WHITE)
            surf.blit(ip_text, (sw // 2 - ip_text.get_width() // 2, 145))

            hint = small_font.render("Share this IP with your friend!", True, GRAY)
            surf.blit(hint, (sw // 2 - hint.get_width() // 2, 175))

            player_count = 1
            if net_host and hasattr(net_host, 'clients'):
                player_count += len(net_host.clients)

            players_text = menu_font.render(f"Players: {player_count}", True, WHITE)
            surf.blit(players_text, (sw // 2 - players_text.get_width() // 2, 210))

            # Player list
            y_off = 280
            label = small_font.render(f"- {local_username} (You - Host)", True, GREEN)
            surf.blit(label, (sw // 2 - 80, y_off))
            y_off += 25
            if net_host and hasattr(net_host, 'clients'):
                usernames = net_host.get_usernames()
                for i, cid in enumerate(net_host.clients):
                    uname = usernames.get(cid, f"Player{cid}")
                    cl = small_font.render(f"- {uname} (Connected)", True, CYAN)
                    surf.blit(cl, (sw // 2 - 80, y_off))
                    y_off += 25

        elif net_mode == "client":
            info = menu_font.render("Connected to host!", True, CYAN)
            surf.blit(info, (sw // 2 - info.get_width() // 2, 110))
            waiting = menu_font.render("Waiting for host to start...", True, GRAY)
            surf.blit(waiting, (sw // 2 - waiting.get_width() // 2, 148))
            you_label = small_font.render(f"Your name: {local_username}", True, GOLD)
            surf.blit(you_label, (sw // 2 - you_label.get_width() // 2, 180))

        # Buttons
        btn_w = 250
        btn_h = 50
        btn_x = sw // 2 - btn_w // 2

        start_btn = None
        if net_mode == "host":
            start_btn = pygame.Rect(btn_x, sh - 160, btn_w, btn_h)
            c = GRAY if start_btn.collidepoint(mx, my) else DARK_GRAY
            pygame.draw.rect(surf, c, start_btn)
            pygame.draw.rect(surf, GREEN, start_btn, 3)
            txt = menu_font.render("START GAME", True, GREEN)
            surf.blit(txt, (start_btn.centerx - txt.get_width() // 2, start_btn.centery - txt.get_height() // 2))

        leave_btn = pygame.Rect(btn_x, sh - 90, btn_w, btn_h)
        c = GRAY if leave_btn.collidepoint(mx, my) else DARK_GRAY
        pygame.draw.rect(surf, c, leave_btn)
        pygame.draw.rect(surf, RED, leave_btn, 3)
        txt = menu_font.render("LEAVE", True, RED)
        surf.blit(txt, (leave_btn.centerx - txt.get_width() // 2, leave_btn.centery - txt.get_height() // 2))

        pygame.display.flip()

        # Check for game start signal (client)
        if net_mode == "client" and net_client:
            for msg in net_client.get_messages():
                msg_type = msg.get("type", "")
                if msg_type == MSG_GAME_START:
                    return "start"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "leave"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if net_mode == "host" and start_btn and start_btn.collidepoint(event.pos):
                    if net_host:
                        net_host.broadcast(MSG_GAME_START, {})
                    return "start"
                if leave_btn.collidepoint(event.pos):
                    return "leave"

        clock_lobby.tick(30)


# ===========================================================
#                   APP ENTRY POINT
# ===========================================================

def main():
    global net_host, net_client, net_mode, remote_players

    try:
        from updater.launcher import run_launcher
        run_launcher()
    except ImportError:
        pass
    except Exception as e:
        print(f"[Updater] Update check failed: {e}")

    display_mgr.apply()

    while True:
        result = show_main_menu()

        if result == "play":
            net_mode = None
            class_key = show_class_selection()
            remote_players = {}
            remote_enemies = {}
            game_result = run_game(class_key)
            if game_result == "restart":
                continue

        elif result == "multiplayer":
            mode, net_obj = show_multiplayer_menu()

            if mode == "back":
                continue

            if mode in ("host", "client"):
                lobby_result = show_lobby()

                if lobby_result == "leave":
                    if net_host:
                        net_host.stop()
                        net_host = None
                    if net_client:
                        net_client.disconnect()
                        net_client = None
                    net_mode = None
                    continue

                if lobby_result == "start":
                    class_key = show_class_selection()
                    remote_players = {}
                    remote_enemies = {}
                    game_result = run_game(class_key)

                    if net_host:
                        net_host.stop()
                        net_host = None
                    if net_client:
                        net_client.disconnect()
                        net_client = None
                    net_mode = None

                    if game_result == "restart":
                        continue


if __name__ == "__main__":
    main()