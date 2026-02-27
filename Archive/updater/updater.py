# updater/updater.py
"""
Update logic — checks version API, downloads updates, stages them.
Supports both Windows (.zip) and Linux (.tar.gz) builds.

Server version.json format (supports both old and new):
  Old: {"version": "x.y.z", "url": "https://...", "changelog": "..."}
  New: {"version": "x.y.z", "url_windows": "https://...", "url_linux": "https://...", "changelog": "..."}

The updater sends ?platform=linux|windows so the server can also route dynamically.
"""

import os
import sys
import json
import shutil
import tarfile
import tempfile
import zipfile
import platform
import subprocess
import stat
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from updater.version import VERSION, VERSION_URL

REQUEST_TIMEOUT = 10
STAGING_DIR_NAME = "_update_staging"

# Build an SSL context — try multiple approaches
_ssl_context = None
try:
    import ssl

    # Try 1: certifi (bundled CA certs, works everywhere)
    try:
        import certifi

        _ssl_context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    # Try 2: system default context
    if _ssl_context is None:
        try:
            ctx = ssl.create_default_context()
            # Quick test: if no CA certs loaded, this will be useless
            _ssl_context = ctx
        except Exception:
            pass
    # Try 3: unverified context as last resort (still encrypted, just no cert check)
    if _ssl_context is None:
        _ssl_context = ssl._create_unverified_context()
except Exception:
    pass


def _get_platform():
    """Return 'windows', 'macos', or 'linux'."""
    s = platform.system().lower()
    if s == "windows":
        return "windows"
    if s == "darwin":
        return "macos"
    return "linux"


def _get_install_dir():
    """Get the root install directory (where the game files live).
    On macOS .app bundles (PyInstaller), files are in Contents/MacOS/."""
    if getattr(sys, 'frozen', False):
        # For PyInstaller, sys.executable is the binary itself
        # On macOS .app: Something.app/Contents/MacOS/RedsGarbageGame
        # Game files (_internal/) are next to it in Contents/MacOS/
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_staging_dir():
    """Get the staging directory path. Uses temp dir if install dir isn't writable."""
    install_dir = _get_install_dir()
    if os.access(install_dir, os.W_OK):
        return os.path.join(install_dir, STAGING_DIR_NAME)
    else:
        # Install dir not writable (e.g. /Applications on macOS)
        import tempfile
        return os.path.join(tempfile.gettempdir(), "rgg_" + STAGING_DIR_NAME)


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


def _urlopen_safe(req, timeout=10):
    """urlopen with SSL fallback — tries verified first, then unverified."""
    import ssl
    # Try with our built context first
    try:
        return urlopen(req, timeout=timeout, context=_ssl_context)
    except URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e.reason):
            print("[Updater] SSL verification failed, retrying without verification...")
            ctx = ssl._create_unverified_context()
            return urlopen(req, timeout=timeout, context=ctx)
        raise


def check_for_update():
    """
    Check the version API for a newer release.
    Sends platform info so the server can return the correct download URL.
    Returns dict with version/url/changelog if update available, else None.
    """
    plat = _get_platform()
    # Append platform query param so server can route if it supports it
    sep = "&" if "?" in VERSION_URL else "?"
    url = f"{VERSION_URL}{sep}platform={plat}"

    print(f"[Updater] Checking {VERSION_URL}  (current: v{VERSION}, platform: {plat})")
    try:
        req = Request(url, headers={
            "User-Agent": f"RGG-Updater/{VERSION} ({plat})",
        })
        resp = _urlopen_safe(req, timeout=REQUEST_TIMEOUT)
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
    changelog = data.get("changelog", "")

    # Pick download URL: prefer platform-specific, fall back to generic
    download_url = ""
    if plat == "windows":
        download_url = data.get("url_windows", "") or data.get("url", "")
    elif plat == "macos":
        download_url = data.get("url_macos", "") or data.get("url", "")
    else:
        download_url = data.get("url_linux", "") or data.get("url", "")

    if not remote_version:
        print(f"[Updater] Invalid response: {data}")
        return None

    if not download_url:
        print(f"[Updater] No download URL for platform '{plat}' in response")
        return None

    if _compare_versions(VERSION, remote_version):
        print(f"[Updater] Update available: v{VERSION} -> v{remote_version} ({plat})")
        return {"version": remote_version, "url": download_url, "changelog": changelog}
    else:
        print(f"[Updater] Up to date (remote: v{remote_version})")
        return None


def check_pending_update():
    """
    Check if a staged update was applied by the helper script.
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
        if os.path.exists(staging):
            try:
                shutil.rmtree(staging)
            except Exception:
                pass
        return True
    return False


def download_update(url, progress_callback=None):
    """Download an update archive (.zip or .tar.gz). Returns path to temp file or None."""
    print(f"[Updater] Downloading: {url}")
    try:
        req = Request(url, headers={"User-Agent": f"RGG-Updater/{VERSION}"})
        resp = _urlopen_safe(req, timeout=60)
        total = int(resp.headers.get("Content-Length", 0))

        # Detect file type from URL or Content-Type
        is_targz = url.endswith(".tar.gz") or url.endswith(".tgz")
        suffix = ".tar.gz" if is_targz else ".zip"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="rgg_update_")
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


def stage_update(archive_path):
    """
    Extract update archive (.zip or .tar.gz) to a staging directory.
    Handles single top-level folder stripping for both formats.
    Preserves file permissions on Linux.
    Returns True on success.
    """
    staging = _get_staging_dir()
    print(f"[Updater] Staging update to: {staging}")

    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging, exist_ok=True)

    try:
        is_targz = archive_path.endswith(".tar.gz") or archive_path.endswith(".tgz")

        if is_targz:
            _extract_targz(archive_path, staging)
        else:
            _extract_zip(archive_path, staging)

        print(f"[Updater] Staging complete")

        # On Linux, make sure any binaries in staging are executable
        if _get_platform() != "windows":
            _fix_permissions(staging)

        # Clean up archive
        try:
            os.remove(archive_path)
        except Exception:
            pass
        return True

    except Exception as e:
        print(f"[Updater] Staging failed: {e}")
        return False


def _extract_zip(zip_path, staging):
    """Extract a .zip archive with top-level folder stripping."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
        strip_prefix = _detect_strip_prefix(names)

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


def _extract_targz(tar_path, staging):
    """Extract a .tar.gz archive with top-level folder stripping."""
    with tarfile.open(tar_path, 'r:gz') as tf:
        names = tf.getnames()
        strip_prefix = _detect_strip_prefix(names)

        # First pass: collect all final paths to know what's a file vs dir
        file_paths = set()
        dir_paths = set()
        for member in tf.getmembers():
            rel_path = member.name
            if strip_prefix and rel_path.startswith(strip_prefix):
                rel_path = rel_path[len(strip_prefix):]
            if not rel_path:
                continue
            if member.isdir():
                dir_paths.add(rel_path)
            else:
                file_paths.add(rel_path)

        # Second pass: extract
        for member in tf.getmembers():
            rel_path = member.name
            if strip_prefix and rel_path.startswith(strip_prefix):
                rel_path = rel_path[len(strip_prefix):]
            if not rel_path:
                continue

            dest = os.path.join(staging, rel_path)

            if member.isdir():
                # Only create directory if no file has the same name
                if rel_path not in file_paths:
                    os.makedirs(dest, exist_ok=True)
            elif member.isfile():
                # If dest exists as a directory, remove it
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                src = tf.extractfile(member)
                if src:
                    with open(dest, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    if member.mode:
                        os.chmod(dest, member.mode)
            elif member.issym():
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                elif os.path.exists(dest):
                    os.remove(dest)
                os.symlink(member.linkname, dest)


def _detect_strip_prefix(names):
    """Detect if all files share a single top-level directory to strip."""
    top_dirs = set()
    for n in names:
        parts = n.split('/')
        if len(parts) > 1 and parts[0]:
            top_dirs.add(parts[0])

    if len(top_dirs) == 1:
        prefix = list(top_dirs)[0] + "/"
        if all(n.startswith(prefix) or n == prefix.rstrip('/') or n == '.' for n in names):
            print(f"[Updater] Stripping prefix: {prefix}")
            return prefix
    return ""


def _fix_permissions(staging):
    """Ensure binaries and scripts in staging are executable on Linux."""
    for root, dirs, files in os.walk(staging):
        for f in files:
            fpath = os.path.join(root, f)
            # Make .sh scripts and the main binary executable
            if f.endswith('.sh') or f == 'RedsGarbageGame' or f == 'run.sh':
                os.chmod(fpath, 0o755)
            # Check if file looks like an ELF binary
            try:
                with open(fpath, 'rb') as fp:
                    magic = fp.read(4)
                if magic == b'\x7fELF':
                    os.chmod(fpath, 0o755)
            except Exception:
                pass


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

    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        exe_dir = os.path.dirname(exe_path)
        launch_cmd = f'start "" "{exe_path}"'
    else:
        main_py = os.path.join(install_dir, "main.py")
        python_exe = sys.executable.replace('"', '""')
        launch_cmd = f'start "" "{python_exe}" "{main_py}"'
        exe_dir = install_dir

    exe_name = os.path.basename(exe_path) if getattr(sys, 'frozen', False) else ""
    bat_content = f'''@echo off
echo Applying update...

:: Kill the game process to release file locks
{'taskkill /f /im "' + exe_name + '" >nul 2>&1' if exe_name else ''}
timeout /t 3 /nobreak >nul

:: Copy all staged files over the install directory
xcopy "{staging}\\*" "{install_dir}\\" /E /Y /Q >nul 2>&1

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
    """Write a shell script for Linux/Mac that preserves permissions."""

    if getattr(sys, 'frozen', False):
        exe = sys.executable
        launch_cmd = f'"{exe}" &'
    else:
        main_py = os.path.join(install_dir, "main.py")
        launch_cmd = f'"{sys.executable}" "{main_py}" &'

    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else install_dir

    # On macOS .app, check if we're inside a bundle and use 'open' to relaunch
    is_macos_app = False
    app_path = None
    if platform.system() == "Darwin" and getattr(sys, 'frozen', False):
        # Walk up from executable to find the .app bundle
        path = os.path.dirname(sys.executable)
        while path and path != "/":
            if path.endswith(".app"):
                app_path = path
                is_macos_app = True
                launch_cmd = f'open "{app_path}" &'
                break
            path = os.path.dirname(path)

    # Check if install dir is writable
    needs_sudo = not os.access(install_dir, os.W_OK)

    if needs_sudo and platform.system() == "Darwin":
        # macOS: use osascript to prompt for admin password
        # Write the update script to a temp location (always writable)
        import tempfile
        sh_path = os.path.join(tempfile.gettempdir(), "_rgg_apply_update.sh")

        sh_content = f'''#!/bin/bash
sleep 2

# Copy staged files with admin privileges
cp -af "{staging}/"* "{install_dir}/"

# Write success marker
echo "done" > "{os.path.join(install_dir, '_update_done.marker')}"

# Clean up staging
rm -rf "{staging}"

# Relaunch (as normal user, not root)
sudo -u "$USER" {launch_cmd}

# Self-delete
rm -f "$0"
'''
        try:
            with open(sh_path, 'w') as f:
                f.write(sh_content)
            os.chmod(sh_path, 0o755)
            print(f"[Updater] Needs admin permissions, prompting...")

            # Use osascript to run the shell script with admin privileges
            # This shows the native macOS password prompt
            subprocess.Popen([
                'osascript', '-e',
                f'do shell script "/bin/bash \\"{sh_path}\\"" with administrator privileges'
            ])
            print("[Updater] Update script launched with admin, exiting game...")
            _exit_game()
            return True
        except Exception as e:
            print(f"[Updater] Failed to launch admin update: {e}")
            return False
    else:
        # Normal case: install dir is writable (Linux, or macOS in ~/Applications)
        sh_path = os.path.join(install_dir, "_apply_update.sh")

        sh_content = f'''#!/bin/bash
sleep 2

# Copy staged files, preserving permissions and symlinks
cp -af "{staging}/"* "{install_dir}/"

# Write success marker
echo "done" > "{os.path.join(install_dir, '_update_done.marker')}"

# Clean up staging
rm -rf "{staging}"

# Relaunch
cd "{exe_dir}"
{launch_cmd}

# Self-delete
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
    """Cleanly exit the game process."""
    try:
        import pygame
        pygame.display.quit()
        pygame.quit()
    except Exception:
        pass
    import time
    time.sleep(0.3)
    os._exit(0)


# Legacy compat
def apply_update(zip_path):
    """Stage + apply in one call (for test_updater.py compat)."""
    if stage_update(zip_path):
        install_dir = _get_install_dir()
        staging = _get_staging_dir()
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