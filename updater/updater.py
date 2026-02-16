# updater/updater.py
"""
Simple updater - Just downloads a ZIP and replaces the EXE.
"""

import os
import sys
import zipfile
import tempfile
import subprocess
import requests
from updater.version import VERSION, VERSION_URL


def check_for_update():
    """Check if there's a new version available."""
    try:
        response = requests.get(VERSION_URL, timeout=10)
        data = response.json()

        remote_version = data.get("version")
        download_url = data.get("url")

        if remote_version != VERSION:
            print(f"[Update] New version available: {remote_version} (current: {VERSION})")
            return {
                "version": remote_version,
                "url": download_url,
                "changelog": data.get("changelog", "")
            }

        print(f"[Update] Up to date ({VERSION})")
        return None

    except Exception as e:
        print(f"[Update] Check failed: {e}")
        return None


def download_and_apply_update(url):
    """Download ZIP and replace the EXE."""
    try:
        # Get the folder where the game EXE is located
        if getattr(sys, 'frozen', False):
            game_folder = os.path.dirname(sys.executable)
            exe_name = os.path.basename(sys.executable)
        else:
            print("[Update] Not running from EXE, skipping update")
            return False

        print(f"[Update] Downloading from {url}")

        # Download the ZIP
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        # Save to temp file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_zip.write(chunk)
        temp_zip.close()

        print(f"[Update] Downloaded to {temp_zip.name}")

        # Extract to temp folder
        temp_extract = tempfile.mkdtemp()
        with zipfile.ZipFile(temp_zip.name, 'r') as zf:
            zf.extractall(temp_extract)

        print(f"[Update] Extracted to {temp_extract}")

        # Find the new EXE in the extracted files
        new_exe = None
        for root, dirs, files in os.walk(temp_extract):
            for file in files:
                if file.endswith('.exe'):
                    new_exe = os.path.join(root, file)
                    break
            if new_exe:
                break

        if not new_exe:
            print("[Update] ERROR: No .exe found in update ZIP!")
            return False

        print(f"[Update] Found new EXE: {new_exe}")

        # Backup old EXE
        old_exe = os.path.join(game_folder, exe_name)
        backup_exe = old_exe + ".bak"

        if os.path.exists(backup_exe):
            os.remove(backup_exe)

        print(f"[Update] Backing up {exe_name} to {exe_name}.bak")
        os.rename(old_exe, backup_exe)

        # Copy new EXE
        import shutil
        print(f"[Update] Installing new EXE")
        shutil.copy2(new_exe, old_exe)

        # Copy _internal folder if it exists
        internal_src = os.path.join(os.path.dirname(new_exe), "_internal")
        internal_dst = os.path.join(game_folder, "_internal")

        if os.path.exists(internal_src):
            print(f"[Update] Updating _internal folder")
            if os.path.exists(internal_dst):
                shutil.rmtree(internal_dst)
            shutil.copytree(internal_src, internal_dst)

        # Cleanup
        os.unlink(temp_zip.name)
        shutil.rmtree(temp_extract)

        print("[Update] Update complete! Restart the game.")
        return True

    except Exception as e:
        print(f"[Update] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def restart_game():
    """Restart the game after update."""
    if getattr(sys, 'frozen', False):
        # Launch a new instance
        subprocess.Popen([sys.executable])
        sys.exit(0)