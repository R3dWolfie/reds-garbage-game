# build.py
"""
Build script to create the EXE using PyInstaller.
Run: python build.py
"""

import PyInstaller.__main__
import os
import shutil

GAME_NAME = "Reds Garbage Game"
ENTRY_POINT = "main.py"
ICON = None  # Set to "assets/icon.ico" if you have one

def build():
    # Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    args = [
        ENTRY_POINT,
        '--name', GAME_NAME,
        '--onedir',            # Use --onefile for single EXE (slower startup)
        '--windowed',          # No console window
        '--add-data', f'assets{os.pathsep}assets',
        '--add-data', f'networking{os.pathsep}networking',
        '--add-data', f'updater{os.pathsep}updater',
        '--hidden-import', 'networking',
        '--hidden-import', 'networking.net_common',
        '--hidden-import', 'networking.net_host',
        '--hidden-import', 'networking.net_client',
        '--hidden-import', 'updater',
        '--hidden-import', 'updater.version',
        '--hidden-import', 'updater.updater',
    ]

    if ICON and os.path.exists(ICON):
        args += ['--icon', ICON]

    print(f"Building {GAME_NAME}...")
    PyInstaller.__main__.run(args)

    # Copy config template
    dist_dir = os.path.join('dist', GAME_NAME)
    if os.path.exists('config.json'):
        shutil.copy('config.json', dist_dir)

    print(f"\nBuild complete! Output: dist/{GAME_NAME}/")
    print(f"Run: dist/{GAME_NAME}/{GAME_NAME}.exe")


if __name__ == "__main__":
    build()
