# updater/updater.py
"""
Update logic — checks version API, downloads updates, applies them.
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from updater.version import VERSION, VERSION_URL

# Timeout for network requests (seconds)
REQUEST_TIMEOUT = 10

# Where we are installed (the directory containing main.py / the .exe)
def _get_install_dir():
    """Get the root install directory of the game."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller .exe
        return os.path.dirname(sys.executable)
    else:
        # Running as .py — go up from updater/ to the project root
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _compare_versions(local, remote):
    """
    Compare two semver strings like '0.1.6' and '0.1.7'.
    Returns True if remote is newer than local.
    """
    try:
        local_parts = [int(x) for x in local.strip().split('.')]
        remote_parts = [int(x) for x in remote.strip().split('.')]
        # Pad to same length
        while len(local_parts) < len(remote_parts):
            local_parts.append(0)
        while len(remote_parts) < len(local_parts):
            remote_parts.append(0)
        return remote_parts > local_parts
    except (ValueError, AttributeError):
        return False


def check_for_update():
    """
    Check the version API for a newer release.

    Expected JSON response from VERSION_URL:
    {
        "version": "0.2.0",
        "url": "https://updates.r3dwolfie.com/releases/v0.2.0.zip",
        "changelog": "Added perma shop, bug fixes"
    }

    Returns the dict if an update is available, or None if up to date.
    Raises on network errors (caller should catch).
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
        print(f"[Updater] Unexpected error checking for updates: {e}")
        return None

    remote_version = data.get("version", "")
    download_url = data.get("url", "")
    changelog = data.get("changelog", "")

    if not remote_version or not download_url:
        print(f"[Updater] Invalid response from server: {data}")
        return None

    if _compare_versions(VERSION, remote_version):
        print(f"[Updater] Update available: v{VERSION} → v{remote_version}")
        return {
            "version": remote_version,
            "url": download_url,
            "changelog": changelog,
        }
    else:
        print(f"[Updater] Up to date (remote: v{remote_version})")
        return None


def download_update(url, progress_callback=None):
    """
    Download an update zip from the given URL.

    Args:
        url: Direct download URL for the update zip.
        progress_callback: Optional callable(downloaded_bytes, total_bytes)
                           called periodically during download.

    Returns the path to the downloaded temp file, or None on failure.
    """
    print(f"[Updater] Downloading: {url}")

    try:
        req = Request(url, headers={"User-Agent": f"RGG-Updater/{VERSION}"})
        resp = urlopen(req, timeout=60)

        # Try to get content length for progress
        total = int(resp.headers.get("Content-Length", 0))

        # Download to a temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip", prefix="rgg_update_")
        downloaded = 0
        chunk_size = 8192

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            tmp.write(chunk)
            downloaded += len(chunk)
            if progress_callback:
                progress_callback(downloaded, total)

        tmp.close()
        print(f"[Updater] Downloaded {downloaded} bytes → {tmp.name}")
        return tmp.name

    except Exception as e:
        print(f"[Updater] Download failed: {e}")
        return None


def apply_update(zip_path):
    """
    Extract the update zip over the current install directory.

    The zip is expected to contain game files at its root (or inside a
    single top-level folder). Files are extracted over the existing install.
    The updater skips overwriting itself and the running executable to
    avoid locked-file issues on Windows.

    Returns True on success, False on failure.
    """
    install_dir = _get_install_dir()
    print(f"[Updater] Applying update from {zip_path} → {install_dir}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Check if everything is inside a single top-level folder
            names = zf.namelist()
            top_dirs = set()
            for n in names:
                parts = n.split('/')
                if len(parts) > 1:
                    top_dirs.add(parts[0])

            # If there's exactly one top-level directory containing everything,
            # strip it so files end up at the install root
            strip_prefix = ""
            if len(top_dirs) == 1:
                prefix = list(top_dirs)[0] + "/"
                all_inside = all(n.startswith(prefix) or n == prefix.rstrip('/') for n in names)
                if all_inside:
                    strip_prefix = prefix
                    print(f"[Updater] Stripping top-level folder: {strip_prefix}")

            # Files to skip (currently running exe, temp files)
            running_exe = ""
            if getattr(sys, 'frozen', False):
                running_exe = os.path.basename(sys.executable).lower()

            extracted = 0
            skipped = 0

            for member in zf.infolist():
                # Strip prefix if needed
                rel_path = member.filename
                if strip_prefix and rel_path.startswith(strip_prefix):
                    rel_path = rel_path[len(strip_prefix):]

                if not rel_path or rel_path.endswith('/'):
                    # Directory entry — ensure it exists
                    dir_path = os.path.join(install_dir, rel_path)
                    os.makedirs(dir_path, exist_ok=True)
                    continue

                # Skip the running executable (Windows locks it)
                if running_exe and rel_path.lower() == running_exe:
                    skipped += 1
                    print(f"[Updater] Skipping locked file: {rel_path}")
                    continue

                # Extract file
                dest = os.path.join(install_dir, rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)

                try:
                    with zf.open(member) as src, open(dest, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    extracted += 1
                except PermissionError:
                    # File is locked (e.g. DLL in use) — try renaming the old
                    # one aside and writing the new one
                    try:
                        backup = dest + ".old"
                        if os.path.exists(backup):
                            os.remove(backup)
                        os.rename(dest, backup)
                        with zf.open(member) as src, open(dest, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        extracted += 1
                    except Exception as inner_e:
                        print(f"[Updater] Could not overwrite {rel_path}: {inner_e}")
                        skipped += 1

            print(f"[Updater] Done — extracted {extracted} files, skipped {skipped}")

        # Clean up the temp zip
        try:
            os.remove(zip_path)
        except Exception:
            pass

        # Clean up any .old backup files from previous updates
        _cleanup_old_files(install_dir)

        return True

    except zipfile.BadZipFile:
        print(f"[Updater] Bad zip file: {zip_path}")
        return False
    except Exception as e:
        print(f"[Updater] Apply failed: {e}")
        return False


def _cleanup_old_files(directory):
    """Remove leftover .old files from previous updates."""
    try:
        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.endswith('.old'):
                    try:
                        os.remove(os.path.join(root, f))
                    except Exception:
                        pass
    except Exception:
        pass


def restart_game():
    """
    Restart the game process.

    For a frozen .exe: re-launch the executable.
    For .py: re-launch with the same Python interpreter.
    """
    print("[Updater] Restarting game...")

    try:
        if getattr(sys, 'frozen', False):
            # PyInstaller .exe — launch the exe again
            exe = sys.executable
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
        else:
            # Running as .py — find and re-run main.py
            install_dir = _get_install_dir()
            main_py = os.path.join(install_dir, "main.py")
            if os.path.exists(main_py):
                subprocess.Popen([sys.executable, main_py], cwd=install_dir)
            else:
                # Fallback: re-run whatever was originally launched
                subprocess.Popen([sys.executable] + sys.argv)
    except Exception as e:
        print(f"[Updater] Restart failed: {e}")
        return  # Don't exit if restart failed

    # Exit current process — use os._exit to guarantee termination
    # (sys.exit can be caught by try/except, os._exit cannot)
    import pygame
    try:
        pygame.quit()
    except Exception:
        pass
    os._exit(0)