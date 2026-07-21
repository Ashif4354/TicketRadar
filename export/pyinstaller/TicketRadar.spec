# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for TicketRadar
# Run from project root: uv run pyinstaller export/pyinstaller/TicketRadar.spec --clean

import os
import sys
import streamlit
from PyInstaller.utils.hooks import copy_metadata

# SPECPATH is auto-defined by PyInstaller as the directory containing this spec file.
# Project root is two levels up from export/pyinstaller/.
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, '..', '..'))

# Get the path to the installed streamlit package
streamlit_dir = os.path.dirname(streamlit.__file__)

# Datas to copy into the executable
datas = [
    # Bootstrap script that Streamlit re-executes as the app
    (os.path.join(ROOT_DIR, "src", "Backend", "main.py"), "."),
    # Streamlit web assets
    (os.path.join(streamlit_dir, "static"), "streamlit/static"),
    (os.path.join(streamlit_dir, "runtime"), "streamlit/runtime"),
]

# Package metadata required by importlib.metadata at runtime
datas += copy_metadata('streamlit')
datas += copy_metadata('pydantic')
datas += copy_metadata('pydantic_settings')

block_cipher = None

a = Analysis(
    [os.path.join(ROOT_DIR, 'src', 'Backend', 'main.py')],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'streamlit',
        'pydantic_settings',
        'aiosmtplib',
        'httpx',
        'bs4',
        'asyncio',
        'watchdog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
