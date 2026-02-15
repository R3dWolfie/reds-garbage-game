# updater/launcher.py
"""
Launcher with update UI. This is the entry point for the EXE.
Shows a splash screen, checks for updates, then launches the game.
"""

import pygame
import sys
import os
import threading

# Make sure we can import from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from updater.version import GAME_NAME, VERSION
from updater.updater import check_for_update, download_update, apply_update, restart_game


def run_launcher():
    """
    Run the update checker. Uses the EXISTING pygame display.
    Does NOT call pygame.init() or pygame.quit().
    """
    # Use the existing display, or create a temporary one
    screen = pygame.display.get_surface()
    if screen is None:
        # No display exists yet — shouldn't happen, but just in case
        screen = pygame.display.set_mode((600, 400))
        pygame.display.set_caption(f"{GAME_NAME} - Launcher")
        created_display = True
    else:
        created_display = False

    clock = pygame.time.Clock()

    font_big = pygame.font.SysFont("Arial", 36, bold=True)
    font_med = pygame.font.SysFont("Arial", 20)
    font_small = pygame.font.SysFont("Arial", 14)

    progress = 0.0
    update_info = None
    state = "checking"

    def check_thread():
        nonlocal update_info, state
        try:
            info = check_for_update()
            if info:
                update_info = info
                state = "found"
            else:
                state = "no_update"
        except Exception as e:
            print(f"[Updater] Check failed: {e}")
            state = "no_update"

    thread = threading.Thread(target=check_thread, daemon=True)
    thread.start()

    def download_thread():
        nonlocal state, progress

        def on_progress(downloaded, total):
            nonlocal progress
            if total > 0:
                progress = downloaded / total

        try:
            path = download_update(update_info["url"], on_progress)
            if path:
                state = "applying"
                success = apply_update(path)
                state = "done" if success else "error"
            else:
                state = "error"
        except Exception as e:
            print(f"[Updater] Download failed: {e}")
            state = "error"

    running = True
    auto_launch_timer = 180  # 3 seconds at 60fps

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_RETURN:
                    if state in ("no_update", "error"):
                        running = False
                    elif state == "found":
                        state = "downloading"
                        dl_thread = threading.Thread(target=download_thread, daemon=True)
                        dl_thread.start()
                    elif state == "done":
                        restart_game()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if state == "found":
                    btn = pygame.Rect(200, 300, 200, 45)
                    if btn.collidepoint(event.pos):
                        state = "downloading"
                        dl_thread = threading.Thread(target=download_thread, daemon=True)
                        dl_thread.start()
                    skip_btn = pygame.Rect(200, 350, 200, 35)
                    if skip_btn.collidepoint(event.pos):
                        running = False

        # Get current screen (might have been resized)
        screen = pygame.display.get_surface()
        screen.fill((20, 20, 30))

        # Title
        title = font_big.render(GAME_NAME, True, (255, 50, 50))
        screen.blit(title, (300 - title.get_width() // 2, 30))

        ver = font_small.render(f"v{VERSION}", True, (150, 150, 150))
        screen.blit(ver, (300 - ver.get_width() // 2, 75))

        if state == "checking":
            txt = font_med.render("Checking for updates...", True, (200, 200, 200))
            screen.blit(txt, (300 - txt.get_width() // 2, 180))

        elif state == "no_update":
            txt = font_med.render("Game is up to date!", True, (0, 255, 0))
            screen.blit(txt, (300 - txt.get_width() // 2, 160))
            hint = font_small.render("Launching game...", True, (150, 150, 150))
            screen.blit(hint, (300 - hint.get_width() // 2, 200))
            auto_launch_timer -= 1
            if auto_launch_timer <= 0:
                running = False

        elif state == "found":
            txt = font_med.render(f"Update available: v{update_info['version']}", True, (255, 255, 0))
            screen.blit(txt, (300 - txt.get_width() // 2, 140))

            cl = font_small.render(update_info.get("changelog", ""), True, (180, 180, 180))
            screen.blit(cl, (300 - cl.get_width() // 2, 175))

            mx, my = pygame.mouse.get_pos()
            btn = pygame.Rect(200, 300, 200, 45)
            c = (80, 80, 80) if btn.collidepoint(mx, my) else (50, 50, 50)
            pygame.draw.rect(screen, c, btn)
            pygame.draw.rect(screen, (0, 255, 0), btn, 2)
            bt = font_med.render("Update Now", True, (0, 255, 0))
            screen.blit(bt, (btn.centerx - bt.get_width() // 2, btn.centery - bt.get_height() // 2))

            skip_btn = pygame.Rect(200, 355, 200, 30)
            c2 = (60, 60, 60) if skip_btn.collidepoint(mx, my) else (40, 40, 40)
            pygame.draw.rect(screen, c2, skip_btn)
            pygame.draw.rect(screen, (150, 150, 150), skip_btn, 1)
            st = font_small.render("Skip (play current version)", True, (150, 150, 150))
            screen.blit(st, (skip_btn.centerx - st.get_width() // 2, skip_btn.centery - st.get_height() // 2))

        elif state == "downloading":
            txt = font_med.render("Downloading update...", True, (100, 200, 255))
            screen.blit(txt, (300 - txt.get_width() // 2, 160))

            bar_w, bar_h = 400, 30
            bar_x, bar_y = 100, 220
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, (0, 150, 255), (bar_x, bar_y, bar_w * progress, bar_h))
            pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 2)
            pct = font_med.render(f"{int(progress * 100)}%", True, (255, 255, 255))
            screen.blit(pct, (300 - pct.get_width() // 2, bar_y + bar_h + 10))

        elif state == "applying":
            txt = font_med.render("Applying update...", True, (255, 200, 0))
            screen.blit(txt, (300 - txt.get_width() // 2, 180))

        elif state == "done":
            txt = font_med.render("Update complete! Restarting...", True, (0, 255, 0))
            screen.blit(txt, (300 - txt.get_width() // 2, 180))
            auto_launch_timer -= 1
            if auto_launch_timer <= 0:
                restart_game()

        elif state == "error":
            txt = font_med.render("Update failed. Press ENTER to play anyway.", True, (255, 80, 80))
            screen.blit(txt, (300 - txt.get_width() // 2, 180))

        pygame.display.flip()
        clock.tick(60)

    # DO NOT call pygame.quit() here!
    # The game needs pygame to stay alive.


if __name__ == "__main__":
    # Only when running launcher.py directly (not from main.py)
    pygame.init()
    pygame.display.set_mode((600, 400))
    run_launcher()
    pygame.quit()
    from main import main
