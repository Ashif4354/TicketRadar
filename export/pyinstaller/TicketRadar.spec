# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for TicketRadar
# Run from project root: cd src/Backend && uv run pyinstaller ../../export/pyinstaller/TicketRadar.spec --clean

import os
import sys
from PyInstaller.utils.hooks import copy_metadata

# SPECPATH is auto-defined by PyInstaller as the directory containing this spec file.
# Project root is two levels up from export/pyinstaller/.
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, '..', '..'))

# Datas to copy into the executable
datas = [
    # Include backend entrypoint
    (os.path.join(ROOT_DIR, "src", "Backend", "main.py"), "."),
    # Include the entire src folder which contains src/Backend and built frontend src/UI/dist
    (os.path.join(ROOT_DIR, "src"), "src"),
]

# Package metadata required by importlib.metadata at runtime
datas += copy_metadata('fastapi')
datas += copy_metadata('uvicorn')
datas += copy_metadata('pydantic')
datas += copy_metadata('pydantic_settings')

block_cipher = None

a = Analysis(
    [os.path.join(ROOT_DIR, 'src', 'Backend', 'main.py')],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'pydantic_settings',
        'aiosmtplib',
        'httpx',
        'bs4',
        'asyncio',
        'platformdirs',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['streamlit', 'altair'],
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
    name='TicketRadar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
