"""
Nuitka build script for TicketRadar.

Why --standalone over --onefile?
  --onefile still extracts to a temp dir on every launch (similar overhead to
  PyInstaller onefile). --standalone pre-extracts once into a folder, so the
  exe boots directly from disk — dramatically faster on low-end hardware.

Usage (from project root):
    cd src/Backend && uv run python ../../export/nuitka/build.py

Output:
    dist/nuitka/TicketRadar.dist/TicketRadar.exe  (the runnable executable)
"""

import os
import sys
import shutil
import subprocess

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DIST_DIR   = os.path.join(ROOT_DIR, 'dist', 'nuitka')

# ---------------------------------------------------------------------------
# Build command
# ---------------------------------------------------------------------------
cmd = [
    sys.executable, '-m', 'nuitka',

    # --- Core mode ---
    '--standalone',                     # onedir: pre-extracted, fastest boot

    # --- Follow all imports automatically ---
    '--follow-imports',

    # --- Packages with heavy dynamic / plugin-style imports ---
    '--include-package=fastapi',
    '--include-package=uvicorn',
    '--include-package=pydantic',
    '--include-package=pydantic_settings',
    '--include-package=aiosmtplib',
    '--include-package=httpx',
    '--include-package=bs4',
    '--include-package=platformdirs',
    '--include-package=attr',
    '--include-package=attrs',
    '--include-package=click',
    '--include-package=packaging',

    # --- Package data (non-Python files shipped inside these packages) ---
    '--include-package-data=pydantic',

    # --- Project source & bootstrap ---
    # Includes the entire src directory (meaning src/Backend/ and src/UI/dist)
    f'--include-data-dir={os.path.join(ROOT_DIR, "src")}=src',

    # --- importlib.metadata (required at runtime) ---
    # Distribution names must match exactly (use hyphens where applicable)
    '--include-distribution-metadata=fastapi',
    '--include-distribution-metadata=uvicorn',
    '--include-distribution-metadata=pydantic',
    '--include-distribution-metadata=pydantic-settings',
    '--include-distribution-metadata=pydantic_core',
    '--include-distribution-metadata=aiosmtplib',
    '--include-distribution-metadata=httpx',
    '--include-distribution-metadata=beautifulsoup4',
    '--include-distribution-metadata=platformdirs',
    '--include-distribution-metadata=click',

    # --- Windows console (force open console so users see logs/errors and closing console kills the app) ---
    '--windows-console-mode=force',

    # --- Output ---
    f'--output-dir={DIST_DIR}',
    '--output-filename=TicketRadar',

    # --- Auto-accept Nuitka C-runtime download prompt ---
    '--assume-yes-for-downloads',

    # --- Limit compilation concurrency to 1 job to prevent RAM exhaustion, overheating, and bit-flips on low-end PCs ---
    '--jobs=1',

    # --- Entry point ---
    os.path.join(ROOT_DIR, 'src', 'Backend', 'main.py'),
]

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
print("=" * 60)
print("  TicketRadar — Nuitka Build")
print("=" * 60)
print(f"  Root  : {ROOT_DIR}")
print(f"  Output: {DIST_DIR}")
print()

os.makedirs(DIST_DIR, exist_ok=True)

try:
    subprocess.run(cmd, check=True, cwd=ROOT_DIR)
except subprocess.CalledProcessError as e:
    print(f"\n[ERROR] Nuitka build failed with exit code {e.returncode}")
    sys.exit(e.returncode)

# ---------------------------------------------------------------------------
# Copy .env.example alongside the executable for first-time users
# ---------------------------------------------------------------------------
# Nuitka names the dist folder after the entry-point script (main.py → main.dist),
# NOT after --output-filename (that only renames the .exe inside the folder).
DIST_FOLDER = os.path.join(DIST_DIR, 'main.dist')

env_example_src = os.path.join(ROOT_DIR, 'src', 'Backend', '.env.example')
env_example_dst = os.path.join(DIST_FOLDER, '.env.example')
if os.path.exists(env_example_src):
    shutil.copy2(env_example_src, env_example_dst)
    print(f"\nCopied .env.example → {env_example_dst}")

print("\n[OK] Build complete!")
print(f"     Executable: {os.path.join(DIST_FOLDER, 'TicketRadar.exe')}")
