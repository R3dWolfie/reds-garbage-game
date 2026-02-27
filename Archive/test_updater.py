#!/usr/bin/env python3
"""
test_updater.py — Drop this in your project root and run it.

What it does:
  1. Starts a local HTTP server on port 9999
  2. Serves a fake version API that reports v99.0.0 (always "newer")
  3. Serves a tiny test zip containing a file called UPDATE_PROOF.txt
  4. Temporarily patches your updater to hit localhost instead of the real server
  5. Runs check → download → apply and shows what happened
  6. Cleans up after itself

Usage:
  cd /path/to/your/game
  python3 test_updater.py
"""

import os
import sys
import json
import zipfile
import tempfile
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from io import BytesIO

# ---- CONFIG ----
TEST_PORT = 9999
FAKE_VERSION = "99.0.0"
FAKE_CHANGELOG = "Test update — if you see UPDATE_PROOF.txt, it worked!"

# ---- Step 1: Create a fake update zip ----
print("=" * 60)
print("  UPDATER TEST TOOL")
print("=" * 60)
print()

# Build a zip in memory with a proof file
zip_buffer = BytesIO()
with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("UPDATE_PROOF.txt", f"Update v{FAKE_VERSION} was applied successfully!\nTimestamp: {time.ctime()}\n")
    zf.writestr("test_subdir/nested_file.txt", "Nested file extraction works too!\n")
zip_bytes = zip_buffer.getvalue()

print(f"[1/5] Created fake update zip ({len(zip_bytes)} bytes)")

# ---- Step 2: Build the version API response ----
version_response = json.dumps({
    "version": FAKE_VERSION,
    "url": f"http://localhost:{TEST_PORT}/update.zip",
    "changelog": FAKE_CHANGELOG,
}).encode()

# ---- Step 3: Start a local HTTP server ----
class TestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(version_response))
            self.end_headers()
            self.wfile.write(version_response)
        elif self.path == "/update.zip":
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", len(zip_bytes))
            self.end_headers()
            self.wfile.write(zip_bytes)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Prefix server logs
        print(f"       [server] {args[0]}")

server = HTTPServer(("localhost", TEST_PORT), TestHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()

print(f"[2/5] Local test server running on http://localhost:{TEST_PORT}")
print(f"       GET /api/version  → reports v{FAKE_VERSION}")
print(f"       GET /update.zip   → {len(zip_bytes)} byte test zip")
print()

# ---- Step 4: Patch and run the updater ----
# Add project root to path so we can import
sys.path.insert(0, os.getcwd())

try:
    from updater.updater import check_for_update, download_update, apply_update, _compare_versions, _get_install_dir
    from updater.version import VERSION
except ImportError as e:
    print(f"[ERROR] Can't import updater: {e}")
    print("        Make sure you run this from your project root directory.")
    server.shutdown()
    sys.exit(1)

print(f"[3/5] Imported updater (current version: v{VERSION})")
print()

# Monkey-patch the VERSION_URL to point at our local server
import updater.version as ver_mod
import updater.updater as upd_mod
original_url = ver_mod.VERSION_URL
ver_mod.VERSION_URL = f"http://localhost:{TEST_PORT}/api/version"
upd_mod.VERSION_URL = ver_mod.VERSION_URL  # updater.py caches this at import

print(f"       Patched VERSION_URL: {original_url}")
print(f"                        →   {ver_mod.VERSION_URL}")
print()

# --- Test version comparison ---
print("[3.5] Testing version comparison:")
assert _compare_versions("0.1.6", "0.1.7") == True, "0.1.6 < 0.1.7 should be True"
assert _compare_versions("0.1.6", "0.1.6") == False, "0.1.6 == 0.1.6 should be False"
assert _compare_versions("1.0.0", "0.9.9") == False, "1.0.0 > 0.9.9 should be False"
assert _compare_versions(VERSION, FAKE_VERSION) == True, f"{VERSION} < {FAKE_VERSION} should be True"
print("       All version comparison tests passed ✓")
print()

# --- Check for update ---
print("[4/5] Checking for update...")
info = check_for_update()
if info is None:
    print("       [FAIL] check_for_update() returned None!")
    print("       The updater thinks you're up to date, but it should see v99.0.0.")
    server.shutdown()
    sys.exit(1)

print(f"       Found update: v{info['version']}")
print(f"       URL: {info['url']}")
print(f"       Changelog: {info.get('changelog', '(none)')}")
print()

# --- Download ---
print("[5/5] Downloading and applying update...")

progress_dots = [0]
def show_progress(downloaded, total):
    pct = int(downloaded / total * 100) if total > 0 else 0
    if pct // 20 > progress_dots[0]:
        progress_dots[0] = pct // 20
        print(f"       Download: {pct}% ({downloaded}/{total} bytes)")

zip_path = download_update(info["url"], show_progress)
if zip_path is None:
    print("       [FAIL] download_update() returned None!")
    server.shutdown()
    sys.exit(1)

print(f"       Downloaded to: {zip_path}")

# --- Apply to a TEMP directory (not the real game!) ---
# Override install dir to a temp location so we don't mess up the real game
test_dir = tempfile.mkdtemp(prefix="rgg_update_test_")
print(f"       Applying to temp dir: {test_dir}")

# Monkey-patch _get_install_dir for safety
original_get_dir = upd_mod._get_install_dir
upd_mod._get_install_dir = lambda: test_dir

success = apply_update(zip_path)

# Restore
upd_mod._get_install_dir = original_get_dir

if not success:
    print("       [FAIL] apply_update() returned False!")
    server.shutdown()
    sys.exit(1)

# --- Verify the files landed ---
print()
print("=" * 60)
print("  RESULTS")
print("=" * 60)

proof_file = os.path.join(test_dir, "UPDATE_PROOF.txt")
nested_file = os.path.join(test_dir, "test_subdir", "nested_file.txt")

all_passed = True

if os.path.exists(proof_file):
    print(f"  ✓ UPDATE_PROOF.txt exists")
    with open(proof_file) as f:
        print(f"    Contents: {f.read().strip()}")
else:
    print(f"  ✗ UPDATE_PROOF.txt NOT FOUND")
    all_passed = False

if os.path.exists(nested_file):
    print(f"  ✓ test_subdir/nested_file.txt exists (nested extraction works)")
else:
    print(f"  ✗ test_subdir/nested_file.txt NOT FOUND")
    all_passed = False

print()
print(f"  Files extracted to {test_dir}:")
for root, dirs, files in os.walk(test_dir):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, test_dir)
        print(f"    {rel}")

print()
if all_passed:
    print("  ✅ ALL TESTS PASSED — Your updater works!")
else:
    print("  ❌ SOME TESTS FAILED — Check the output above.")

# Cleanup
print()
print(f"  Temp dir left at: {test_dir}")
print(f"  (delete it whenever: rm -rf {test_dir})")

server.shutdown()