# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import streamlit
from PyInstaller.utils.hooks import copy_metadata

# Get the path to the streamlit package
streamlit_dir = os.path.dirname(streamlit.__file__)

# Datas to copy into the executable
datas = [
    ("main.py", "."),
    (os.path.join(streamlit_dir, "static"), "streamlit/static"),
    (os.path.join(streamlit_dir, "runtime"), "streamlit/runtime"),
]

# Add metadata for Streamlit and Pydantic
datas += copy_metadata('streamlit')
datas += copy_metadata('pydantic')
datas += copy_metadata('pydantic_settings')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'streamlit',
        'pydantic_settings',
        'aiosmtplib',
        'httpx',
        'playwright',
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
