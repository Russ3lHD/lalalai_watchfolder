# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Lalal AI lalalAI_Watchfolder
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('Watchfolder-icon.ico', '.')],
    hiddenimports=[
        'tkinter',
        'requests',
        'cryptography',
        'watchdog',
        # Include watchdog observer backends explicitly so PyInstaller doesn't omit them
        'watchdog.observers.winapi',
        'watchdog.observers.read_directory_changes',
        'watchdog.observers.polling',
        'watchdog.observers.inotify',
        'watchdog.observers.fsevents',
        'watchdog.events',
        'watchdog.utils',
        'pillow',
        'psutil',
        'sv_ttk',
        'tktooltip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/runtime_hooks/watchdog_runtime_hook.py'],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lalalAI_Watchfolder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Watchfolder-icon.ico',  # Application icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lalalAI_Watchfolder',
)
