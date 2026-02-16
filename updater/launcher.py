# updater/launcher.py
"""
Launcher with update UI. Called from main.py on startup.
Shows a splash screen, checks for updates, then returns to let the game run.
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
        screen = pygame.display.set_mode((600, 400))
        pygame.display.set_caption(f"{GAME_NAME} - Launcher")

    clock = pygame.time.Clock()

    font_big = pygame.font.SysFont("Arial", 36, bold=True)
    font_med = pygame.font.SysFont("Arial", 20)
    font_small = pygame.font.SysFont("Arial", 14)

    progress = 0.0
    update_info = None
    error_message = ""
    state = "checking"  # checking, found, downloading, applying, done, no_update, error

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

    # Start the version check immediately
    thread = threading.Thread(target=check_thread, daemon=True)
    thread.start()

    def download_thread():
        nonlocal state, progress, error_message

        def on_progress(downloaded, total):
            nonlocal progress
            if total > 0:
                progress = downloaded / total

        try:
            path = download_update(update_info["url"], on_progress)
            if path:
                state = "applying"
                success = apply_update(path)
                if success:
                    state = "done"
                else:
                    state = "error"
                    error_message = "Failed to apply update"
            else:
                state = "error"
                error_message = "Download failed"
        except Exception as e:
            print(f"[Updater] Download failed: {e}")
            state = "error"
            error_message = str(e)[:60]

    running = True
    auto_launch_timer = 180  # 3 seconds at 60fps
    auto_restart_timer = 120  # 2 seconds after "done"

    while running:
        screen = pygame.display.get_surface()
        sw = screen.get_width()
        sh = screen.get_height()
        cx = sw // 2  # Horizontal center

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
                        progress = 0.0
                        dl_thread = threading.Thread(target=download_thread, daemon=True)
                        dl_thread.start()
                    elif state == "done":
                        restart_game()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "found":
                    # Check "Update Now" button
                    btn = pygame.Rect(cx - 100, sh // 2 + 60, 200, 45)
                    if btn.collidepoint(event.pos):
                        state = "downloading"
                        progress = 0.0
                        dl_thread = threading.Thread(target=download_thread, daemon=True)
                        dl_thread.start()
                    # Check "Skip" button
                    skip_btn = pygame.Rect(cx - 100, sh // 2 + 115, 200, 30)
                    if skip_btn.collidepoint(event.pos):
                        running = False

        # ---- DRAW ----
        screen.fill((20, 20, 30))

        # Title
        title = font_big.render(GAME_NAME, True, (255, 50, 50))
        screen.blit(title, (cx - title.get_width() // 2, sh // 4 - 40))

        ver = font_small.render(f"v{VERSION}", True, (150, 150, 150))
        screen.blit(ver, (cx - ver.get_width() // 2, sh // 4 + 10))

        mid_y = sh // 2 - 30  # Vertical center for status text

        if state == "checking":
            dots = "." * ((pygame.time.get_ticks() // 400) % 4)
            txt = font_med.render(f"Checking for updates{dots}", True, (200, 200, 200))
            screen.blit(txt, (cx - txt.get_width() // 2, mid_y))

        elif state == "no_update":
            txt = font_med.render("Game is up to date!", True, (0, 255, 0))
            screen.blit(txt, (cx - txt.get_width() // 2, mid_y))

            auto_launch_timer -= 1
            seconds_left = max(0, auto_launch_timer // 60)
            hint = font_small.render(f"Launching game in {seconds_left}s... (ENTER to skip)", True, (150, 150, 150))
            screen.blit(hint, (cx - hint.get_width() // 2, mid_y + 35))

            if auto_launch_timer <= 0:
                running = False

        elif state == "found":
            txt = font_med.render(f"Update available: v{update_info['version']}", True, (255, 255, 0))
            screen.blit(txt, (cx - txt.get_width() // 2, mid_y - 20))

            changelog = update_info.get("changelog", "")
            if changelog:
                cl = font_small.render(changelog[:80], True, (180, 180, 180))
                screen.blit(cl, (cx - cl.get_width() // 2, mid_y + 15))

            # "Update Now" button
            mx, my = pygame.mouse.get_pos()
            btn = pygame.Rect(cx - 100, sh // 2 + 60, 200, 45)
            c = (80, 80, 80) if btn.collidepoint(mx, my) else (50, 50, 50)
            pygame.draw.rect(screen, c, btn)
            pygame.draw.rect(screen, (0, 255, 0), btn, 2)
            bt = font_med.render("Update Now", True, (0, 255, 0))
            screen.blit(bt, (btn.centerx - bt.get_width() // 2, btn.centery - bt.get_height() // 2))

            # "Skip" button
            skip_btn = pygame.Rect(cx - 100, sh // 2 + 115, 200, 30)
            c2 = (60, 60, 60) if skip_btn.collidepoint(mx, my) else (40, 40, 40)
            pygame.draw.rect(screen, c2, skip_btn)
            pygame.draw.rect(screen, (150, 150, 150), skip_btn, 1)
            st = font_small.render("Skip (play current version)", True, (150, 150, 150))
            screen.blit(st, (skip_btn.centerx - st.get_width() // 2, skip_btn.centery - st.get_height() // 2))

        elif state == "downloading":
            txt = font_med.render("Downloading update...", True, (100, 200, 255))
            screen.blit(txt, (cx - txt.get_width() // 2, mid_y - 10))

            # Progress bar
            bar_w = min(400, sw - 100)
            bar_h = 30
            bar_x = cx - bar_w // 2
            bar_y = mid_y + 30
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, (0, 150, 255), (bar_x, bar_y, int(bar_w * progress), bar_h))
            pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 2)

            pct = font_med.render(f"{int(progress * 100)}%", True, (255, 255, 255))
            screen.blit(pct, (cx - pct.get_width() // 2, bar_y + bar_h + 8))

        elif state == "applying":
            txt = font_med.render("Applying update...", True, (255, 200, 0))
            screen.blit(txt, (cx - txt.get_width() // 2, mid_y))

        elif state == "done":
            txt = font_med.render("Update complete! Restarting...", True, (0, 255, 0))
            screen.blit(txt, (cx - txt.get_width() // 2, mid_y))

            auto_restart_timer -= 1
            if auto_restart_timer <= 0:
                restart_game()

        elif state == "error":
            txt = font_med.render("Update failed", True, (255, 80, 80))
            screen.blit(txt, (cx - txt.get_width() // 2, mid_y - 10))

            if error_message:
                err = font_small.render(error_message[:60], True, (200, 150, 150))
                screen.blit(err, (cx - err.get_width() // 2, mid_y + 20))

            hint = font_small.render("Press ENTER to play anyway, or ESC to quit", True, (150, 150, 150))
            screen.blit(hint, (cx - hint.get_width() // 2, mid_y + 50))

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