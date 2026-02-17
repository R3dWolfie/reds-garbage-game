# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Red's Garbage Game — Linux build

import os
import sys

block_cipher = None

# Get the project root
project_root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        # Include assets dir if it exists
        (os.path.join(project_root, 'assets'), 'assets')
        if os.path.isdir(os.path.join(project_root, 'assets')) else
        ('.', '.'),  # dummy, filtered below
    ],
    hiddenimports=[
        'pygame',
        'numpy',
        'core',
        'core.settings',
        'core.game_state',
        'core.sound_manager',
        'core.sprite_loader',
        'entities',
        'entities.player_base',
        'entities.player_default',
        'entities.player_tank',
        'entities.player_laser',
        'entities.player_gunner',
        'entities.player_sniper',
        'entities.player_paladin',
        'entities.enemy',
        'entities.objects',
        'entities.remote_ghosts',
        'game',
        'game.loop',
        'game.helpers',
        'ui',
        'ui.menus',
        'ui.hud',
        'ui.upgrade_menu',
        'ui.settings_menu',
        'ui.perma_shop',
        'ui.hat_menu',
        'ui.multiplayer_menus',
        'ui.username_input',
        'ui.vfx',
        'networking',
        'networking.net_common',
        'networking.net_host',
        'networking.net_client',
        'networking.net_relay',
        'networking.lobby_client',
        'updater',
        'updater.updater',
        'updater.launcher',
        'updater.version',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'xmlrpc', 'pydoc'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out dummy datas entry
a.datas = [d for d in a.datas if d[0] != '.']

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RedsGarbageGame',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,  # No terminal window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='RedsGarbageGame',
)
