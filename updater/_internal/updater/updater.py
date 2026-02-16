# updater/updater.py
"""
Auto-updater that checks your server for new versions.
Server should expose:
  GET /api/version  -> {"version": "0.2.0", "url": "https://your-server.com/downloads/reds_garbage_game_0.2.0.zip", "changelog": "Fixed stuff"}
  GET /downloads/<file> -> the actual zip/exe
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
import requests
from updater.version import VERSION, VERSION_URL, GAME_NAME


def get_install_dir():
    """Get the directory where the game is installed."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def parse_version(v):
    """Convert '0.1.0' to tuple (0, 1, 0) for comparison."""
    return tuple(int(x) for x in v.strip().split('.'))


def check_for_update():
    """
    Check the server for a newer version.
    Returns dict with update info or None if up to date.
    """
    try:
        response = requests.get(VERSION_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        remote_version = data.get("version", VERSION)
        if parse_version(remote_version) > parse_version(VERSION):
            return {
                "version": remote_version,
                "url": data.get("url", ""),
                "changelog": data.get("changelog", "No changelog provided."),
                "mandatory": data.get("mandatory", False),
            }
        return None
    except Exception as e:
        print(f"[Updater] Could not check for updates: {e}")
        return None


def download_update(url, progress_callback=None):
    """
    Download the update zip to a temp file.
    progress_callback(downloaded_bytes, total_bytes) is called during download.
    Returns the path to the downloaded file.
    """
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        total = int(response.headers.get('content-length', 0))

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        downloaded = 0

        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                tmp.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    progress_callback(downloaded, total)

        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"[Updater] Download failed: {e}")
        return None


def apply_update(zip_path):
    """
    Extract the update zip over the current installation.
    The zip should contain the game files at root level.
    """
    install_dir = get_install_dir()

    try:
        # Extract to temp dir first
        temp_extract = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_extract)

        # Copy new files over
        for item in os.listdir(temp_extract):
            src = os.path.join(temp_extract, item)
            dst = os.path.join(install_dir, item)

            # Don't overwrite config or saves
            if item in ('config.json', 'saves'):
                continue

            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                # On Windows, running EXEs are locked and can't be overwritten.
                # Rename the old file out of the way first, then copy the new one.
                # The old .bak file gets cleaned up on next launch.
                if os.path.exists(dst):
                    bak = dst + ".bak"
                    if os.path.exists(bak):
                        try:
                            os.remove(bak)
                        except Exception:
                            pass
                    try:
                        os.rename(dst, bak)
                    except Exception:
                        pass  # If rename fails, try copy anyway
                shutil.copy2(src, dst)

        # Clean up old .bak files from previous updates
        for f in os.listdir(install_dir):
            if f.endswith(".bak"):
                try:
                    os.remove(os.path.join(install_dir, f))
                except Exception:
                    pass  # Still locked, will be cleaned next time

        # Cleanup temp files
        shutil.rmtree(temp_extract, ignore_errors=True)
        try:
            os.unlink(zip_path)
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"[Updater] Apply failed: {e}")
        return False


def restart_game():
    """Restart the game executable after an update."""
    if getattr(sys, 'frozen', False):
        exe = sys.executable
        subprocess.Popen([exe])
        sys.exit(0)
    else:
        python = sys.executable
        subprocess.Popen([python] + sys.argv)
        sys.exit(0)