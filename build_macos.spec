# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Red's Garbage Game — macOS build

import os
import sys

block_cipher = None

project_root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, 'assets'), 'assets')
        if os.path.isdir(os.path.join(project_root, 'assets')) else
        ('.', '.'),
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
    cipher=block_cipher,
    noarchive=False,
)

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
    upx=False,  # UPX not reliable on macOS
    console=False,
)

# macOS .app bundle
app = BUNDLE(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Red's Garbage Game.app",
    icon=os.path.join(project_root, 'assets', 'icon.icns')
    if os.path.exists(os.path.join(project_root, 'assets', 'icon.icns'))
    else None,
    bundle_identifier='com.r3dwolfie.redsgarbagegame',
    info_plist={
        'CFBundleName': "Red's Garbage Game",
        'CFBundleDisplayName': "Red's Garbage Game",
        'CFBundleShortVersionString': '0.3.3',
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
    },
)

# Also create a plain folder build for the tar.gz distribution
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    name='RedsGarbageGame',
)
