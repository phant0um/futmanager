# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — FUTMANAGER (GUI nativa Tkinter)
Gera FutManager.app windowed (sem terminal), DB empacotada.

Uso:
    python3 -m PyInstaller futmanager.spec --noconfirm
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('data/futmanager.db', 'data'),     # DB inicial empacotada
        ('web/static', 'web/static'),       # frontend web (modo --web)
    ],
    hiddenimports=[
        'gameapi',
        'gui.app',
        'web.server',
        'engine.season',
        'engine.simulation',
        'engine.career',
        'engine.finance',
        'engine.transfer',
        'engine.manager',
        'engine.coach',
        'engine.live',
        'engine.lineup',
        'engine.cup',
        'engine.copa',
        'engine.calendar',
        'engine.estadual',
        'scripts.add_brazil_extra',
        'db.models',
        'db.migrate_career',
        'ui.cli',
        'ui.career',
        'scripts.generate_squads',
        'scripts.seed_top_players',
        'paths',
        'saves',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy', 'pandas', 'matplotlib', 'scipy',  # zero deps pesadas
        'PIL', 'PyQt5', 'PyQt6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: binaries vão no COLLECT
    name='futmanager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # janela GUI (sem terminal)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,       # arch nativa (arm64 neste Mac)
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='futmanager',
)

app = BUNDLE(
    coll,
    name='FutManager.app',
    icon=None,
    bundle_identifier='com.futmanager.game',
    info_plist={
        'CFBundleName': 'FutManager',
        'CFBundleDisplayName': 'FUTMANAGER',
        'CFBundleShortVersionString': '1.0',
        'CFBundleVersion': '1.0.0',
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
    },
)
