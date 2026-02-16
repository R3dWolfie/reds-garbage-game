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
from ui.menus import show_main_menu, show_class_selection
from ui.multiplayer_menus import show_multiplayer_menu, show_lobby
from game.loop import run_game


def main():
    # Run the updater/launcher
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
            gs.net_mode = None
            class_key, starting_wave = show_class_selection()
            gs.remote_players = {}
            gs.remote_enemies = {}
            game_result = run_game(class_key, starting_wave)
            if game_result == "restart":
                continue

        elif result == "multiplayer":
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
                    class_key, starting_wave = show_class_selection()
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