# main.py
"""
Red's Garbage Game — Entry point.
Imports all modules and runs the main loop.
"""

import pygame
import sys

# Initialize shared state (pygame.init happens here)
from core.game_state import display_mgr, gs

# Import screens
from ui.menus import show_main_menu, show_class_selection, show_play_mode
from ui.multiplayer_menus import show_multiplayer_menu, show_lobby
from game.loop import run_game


def _show_restart_prompt(running_ver, disk_ver):
    """Show a message telling the user to restart to finish updating."""
    import subprocess, os
    screen = display_mgr.get_screen()
    clock = pygame.time.Clock()
    font_big = pygame.font.SysFont("Arial", 28, bold=True)
    font_med = pygame.font.SysFont("Arial", 20)
    font_small = pygame.font.SysFont("Arial", 14)

    # Try auto-restart first
    try:
        install_dir = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable], cwd=os.path.dirname(sys.executable))
        else:
            main_py = os.path.join(install_dir, "main.py")
            subprocess.Popen([sys.executable, main_py], cwd=install_dir)
        pygame.display.quit()
        pygame.quit()
        os._exit(0)
    except Exception as e:
        print(f"[Main] Auto-restart failed: {e}")

    # If auto-restart failed, show manual prompt
    while True:
        sw, sh = screen.get_size()
        cx = sw // 2
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    pygame.quit(); sys.exit()

        screen.fill((20, 20, 30))
        t1 = font_big.render("Update Downloaded!", True, (0, 255, 0))
        screen.blit(t1, (cx - t1.get_width()//2, sh//3))
        t2 = font_med.render(f"v{running_ver}  ->  v{disk_ver}", True, (255, 255, 0))
        screen.blit(t2, (cx - t2.get_width()//2, sh//3 + 45))
        t3 = font_med.render("Please close and reopen the game", True, (200, 200, 200))
        screen.blit(t3, (cx - t3.get_width()//2, sh//2 + 10))
        t4 = font_small.render("Press ENTER or ESC to close", True, (120, 120, 120))
        screen.blit(t4, (cx - t4.get_width()//2, sh//2 + 50))
        pygame.display.flip()
        clock.tick(30)


def main():
    # Check if an update was applied and we need to notify user
    try:
        from updater.updater import check_pending_update
        if check_pending_update():
            print("[Main] Update was applied on last restart!")
    except Exception:
        pass

    # Run the updater/launcher
    try:
        from updater.launcher import run_launcher
        run_launcher()
    except SystemExit:
        import os
        os._exit(0)
    except ImportError:
        pass
    except Exception as e:
        print(f"[Updater] Update check failed: {e}")

    # After updater runs, check if on-disk version differs from running version
    # (means the old updater extracted new files but couldn't restart properly)
    try:
        from updater.version import VERSION as RUNNING_VERSION
        import os
        version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "updater", "version.py")
        disk_version = None
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                for line in f:
                    if line.startswith("VERSION"):
                        disk_version = line.split("=")[1].strip().strip('"').strip("'")
                        break
        if disk_version and disk_version != RUNNING_VERSION:
            print(f"[Main] Version mismatch! Running: {RUNNING_VERSION}, On disk: {disk_version}")
            _show_restart_prompt(RUNNING_VERSION, disk_version)
    except Exception as e:
        print(f"[Main] Version check skipped: {e}")

    display_mgr.apply()

    while True:
        result = show_main_menu()

        if result == "play":
            play_mode = show_play_mode()

            if play_mode == "back":
                continue

            if play_mode == "singleplayer":
                gs.net_mode = None
                result = show_class_selection()
                if result[0] == "back":
                    continue
                class_key, starting_wave = result
                gs.remote_players = {}
                gs.remote_enemies = {}
                game_result = run_game(class_key, starting_wave)
                if game_result == "restart":
                    continue

            elif play_mode == "multiplayer":
                mode, net_obj = show_multiplayer_menu()

                if mode == "back":
                    continue

                if mode in ("host", "client"):
                    lobby_result = show_lobby()

                    if lobby_result == "leave":
                        if gs.net_host:
                            gs.net_host.stop()
                            gs.net_host = None
                        if gs.net_client:
                            gs.net_client.disconnect()
                            gs.net_client = None
                        gs.net_mode = None
                        continue

                    if lobby_result == "start":
                        result = show_class_selection()
                        if result[0] == "back":
                            continue
                        class_key, starting_wave = result
                        gs.remote_players = {}
                        gs.remote_enemies = {}
                        game_result = run_game(class_key, starting_wave)

                        if gs.net_host:
                            gs.net_host.stop()
                            gs.net_host = None
                        if gs.net_client:
                            gs.net_client.disconnect()
                            gs.net_client = None
                        gs.net_mode = None

                        if game_result == "restart":
                            continue


if __name__ == "__main__":
    main()