# updater/updater.py
"""
Update logic — checks version API, downloads updates, stages them.
Uses a two-stage approach for Windows compatibility:
  1. Download zip → extract to _update_staging/
  2. Write a helper script that copies staged files after game exits
  3. Helper script launches the new version
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import platform
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from updater.version import VERSION, VERSION_URL

REQUEST_TIMEOUT = 10
STAGING_DIR_NAME = "_update_staging"


def _get_install_dir():
    """Get the directory where Python source files live."""
    if getattr(sys, 'frozen', False):
        # PyInstaller puts Python files in _internal/ next to the .exe
        exe_dir = os.path.dirname(sys.executable)
        internal = os.path.join(exe_dir, "_internal")
        if os.path.isdir(internal):
            return internal
        return exe_dir
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_staging_dir():
    """Get the staging directory path."""
    return os.path.join(_get_install_dir(), STAGING_DIR_NAME)


def _compare_versions(local, remote):
    """Returns True if remote is newer than local."""
    try:
        lp = [int(x) for x in local.strip().split('.')]
        rp = [int(x) for x in remote.strip().split('.')]
        while len(lp) < len(rp): lp.append(0)
        while len(rp) < len(lp): rp.append(0)
        return rp > lp
    except (ValueError, AttributeError):
        return False


def check_for_update():
    """
    Check the version API for a newer release.
    Returns dict with version/url/changelog if update available, else None.
    """
    print(f"[Updater] Checking {VERSION_URL}  (current: v{VERSION})")
    try:
        req = Request(VERSION_URL, headers={"User-Agent": f"RGG-Updater/{VERSION}"})
        resp = urlopen(req, timeout=REQUEST_TIMEOUT)
        data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"[Updater] HTTP error {e.code}: {e.reason}")
        return None
    except URLError as e:
        print(f"[Updater] Connection failed: {e.reason}")
        return None
    except Exception as e:
        print(f"[Updater] Unexpected error: {e}")
        return None

    remote_version = data.get("version", "")
    download_url = data.get("url", "")
    changelog = data.get("changelog", "")

    if not remote_version or not download_url:
        print(f"[Updater] Invalid response: {data}")
        return None

    if _compare_versions(VERSION, remote_version):
        print(f"[Updater] Update available: v{VERSION} -> v{remote_version}")
        return {"version": remote_version, "url": download_url, "changelog": changelog}
    else:
        print(f"[Updater] Up to date (remote: v{remote_version})")
        return None


def check_pending_update():
    """
    Check if a staged update was applied by the helper script.
    If _update_staging exists and is empty or has a 'done' marker, clean it up.
    Returns True if an update was just applied.
    """
    staging = _get_staging_dir()
    done_marker = os.path.join(_get_install_dir(), "_update_done.marker")

    if os.path.exists(done_marker):
        print("[Updater] Update was applied successfully on last restart!")
        try:
            os.remove(done_marker)
        except Exception:
            pass
        # Clean up staging dir
        if os.path.exists(staging):
            try:
                shutil.rmtree(staging)
            except Exception:
                pass
        return True
    return False


def download_update(url, progress_callback=None):
    """Download an update zip. Returns path to temp file or None."""
    print(f"[Updater] Downloading: {url}")
    try:
        req = Request(url, headers={"User-Agent": f"RGG-Updater/{VERSION}"})
        resp = urlopen(req, timeout=60)
        total = int(resp.headers.get("Content-Length", 0))

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip", prefix="rgg_update_")
        downloaded = 0
        while True:
            chunk = resp.read(8192)
            if not chunk:
                break
            tmp.write(chunk)
            downloaded += len(chunk)
            if progress_callback:
                progress_callback(downloaded, total)
        tmp.close()
        print(f"[Updater] Downloaded {downloaded} bytes -> {tmp.name}")
        return tmp.name
    except Exception as e:
        print(f"[Updater] Download failed: {e}")
        return None


def stage_update(zip_path):
    """
    Extract update zip to a staging directory.
    Does NOT overwrite any game files yet.
    Returns True on success.
    """
    staging = _get_staging_dir()
    print(f"[Updater] Staging update to: {staging}")

    # Clean old staging
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            # Detect single top-level folder
            top_dirs = set()
            for n in names:
                parts = n.split('/')
                if len(parts) > 1:
                    top_dirs.add(parts[0])

            strip_prefix = ""
            if len(top_dirs) == 1:
                prefix = list(top_dirs)[0] + "/"
                if all(n.startswith(prefix) or n == prefix.rstrip('/') for n in names):
                    strip_prefix = prefix
                    print(f"[Updater] Stripping prefix: {strip_prefix}")

            for member in zf.infolist():
                rel_path = member.filename
                if strip_prefix and rel_path.startswith(strip_prefix):
                    rel_path = rel_path[len(strip_prefix):]
                if not rel_path or rel_path.endswith('/'):
                    os.makedirs(os.path.join(staging, rel_path), exist_ok=True)
                    continue
                dest = os.path.join(staging, rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(member) as src, open(dest, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

        print(f"[Updater] Staging complete")
        # Clean up zip
        try:
            os.remove(zip_path)
        except Exception:
            pass
        return True

    except Exception as e:
        print(f"[Updater] Staging failed: {e}")
        return False


def apply_staged_update_and_restart():
    """
    Write a helper script that:
      1. Waits for this process to exit
      2. Copies staged files over the install directory
      3. Writes a done marker
      4. Relaunches the game
      5. Deletes itself
    Then exit this process.
    """
    install_dir = _get_install_dir()
    staging = _get_staging_dir()

    if not os.path.exists(staging):
        print("[Updater] No staged update found!")
        return False

    if platform.system() == "Windows":
        return _apply_windows(install_dir, staging)
    else:
        return _apply_unix(install_dir, staging)


def _apply_windows(install_dir, staging):
    """Write a .bat script that copies files after game exits."""
    bat_path = os.path.join(install_dir, "_apply_update.bat")

    # Figure out what to launch after update
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable  # Full path to the .exe
        exe_dir = os.path.dirname(exe_path)
        launch_cmd = f'start "" "{exe_path}"'
    else:
        main_py = os.path.join(install_dir, "main.py")
        python_exe = sys.executable.replace('"', '""')
        launch_cmd = f'start "" "{python_exe}" "{main_py}"'
        exe_dir = install_dir

    # Batch script: wait, xcopy, marker, relaunch, self-delete
    bat_content = f'''@echo off
echo Applying update...
:: Wait for the game process to fully exit
timeout /t 2 /nobreak >nul

:: Copy all staged files over the install directory
xcopy "{staging}\\*" "{install_dir}\\" /E /Y /Q >nul 2>&1
if errorlevel 1 (
    echo Update copy failed, retrying...
    timeout /t 2 /nobreak >nul
    xcopy "{staging}\\*" "{install_dir}\\" /E /Y /Q >nul 2>&1
)

:: Write success marker
echo done > "{os.path.join(install_dir, '_update_done.marker')}"

:: Clean up staging
rmdir /S /Q "{staging}" >nul 2>&1

:: Relaunch the game
cd /d "{exe_dir}"
{launch_cmd}

:: Delete this script
del "%~f0" >nul 2>&1
'''

    try:
        with open(bat_path, 'w') as f:
            f.write(bat_content)
        print(f"[Updater] Wrote update script: {bat_path}")

        # Launch the bat script hidden (minimized)
        subprocess.Popen(
            ['cmd', '/c', bat_path],
            cwd=install_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0x08000000,
        )
        print("[Updater] Update script launched, exiting game...")
        _exit_game()
        return True

    except Exception as e:
        print(f"[Updater] Failed to write update script: {e}")
        return False


def _apply_unix(install_dir, staging):
    """Write a shell script for Linux/Mac."""
    sh_path = os.path.join(install_dir, "_apply_update.sh")

    if getattr(sys, 'frozen', False):
        exe = sys.executable  # Full path
        launch_cmd = f'"{exe}" &'
    else:
        main_py = os.path.join(install_dir, "main.py")
        launch_cmd = f'"{sys.executable}" "{main_py}" &'

    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else install_dir

    sh_content = f'''#!/bin/bash
sleep 2
cp -rf "{staging}/"* "{install_dir}/"
echo "done" > "{os.path.join(install_dir, '_update_done.marker')}"
rm -rf "{staging}"
cd "{exe_dir}"
{launch_cmd}
rm -f "$0"
'''

    try:
        with open(sh_path, 'w') as f:
            f.write(sh_content)
        os.chmod(sh_path, 0o755)
        print(f"[Updater] Wrote update script: {sh_path}")

        subprocess.Popen(['/bin/bash', sh_path], cwd=install_dir)
        print("[Updater] Update script launched, exiting game...")
        _exit_game()
        return True

    except Exception as e:
        print(f"[Updater] Failed to write update script: {e}")
        return False


def _exit_game():
    """Cleanly exit the game process — close window, then terminate."""
    try:
        import pygame
        pygame.display.quit()
        pygame.quit()
    except Exception:
        pass
    # Small delay to let the bat script know we're closing
    import time
    time.sleep(0.3)
    os._exit(0)


# Legacy compat
def apply_update(zip_path):
    """Stage + apply in one call (for test_updater.py compat)."""
    if stage_update(zip_path):
        install_dir = _get_install_dir()
        staging = _get_staging_dir()
        # Direct copy (used in tests where we don't need process restart)
        try:
            for root, dirs, files in os.walk(staging):
                for f in files:
                    src = os.path.join(root, f)
                    rel = os.path.relpath(src, staging)
                    dst = os.path.join(install_dir, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
            shutil.rmtree(staging)
            return True
        except Exception as e:
            print(f"[Updater] Direct apply failed: {e}")
            return False
    return False


def restart_game():
    """Legacy — just restart without update."""
    print("[Updater] Restarting game...")
    try:
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable], cwd=os.path.dirname(sys.executable))
        else:
            install_dir = _get_install_dir()
            main_py = os.path.join(install_dir, "main.py")
            if os.path.exists(main_py):
                subprocess.Popen([sys.executable, main_py], cwd=install_dir)
            else:
                subprocess.Popen([sys.executable] + sys.argv)
    except Exception as e:
        print(f"[Updater] Restart failed: {e}")
        return
    _exit_game()