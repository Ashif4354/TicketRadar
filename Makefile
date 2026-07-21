# Makefile for TicketRadar

.PHONY: install build build-pyinstaller build-nuitka run clean

# Default target
all: build-nuitka

# Install all dependencies using uv
install:
	uv sync

# ── Build targets ──────────────────────────────────────────────────────────────

# Build with Nuitka (standalone, fastest boot — recommended)
build-nuitka:
	uv run python export/nuitka/build.py

# Build with PyInstaller (single onefile exe — portable but slower boot)
build-pyinstaller:
	uv run pyinstaller export/pyinstaller/TicketRadar.spec --clean \
		--distpath dist/pyinstaller \
		--workpath build/pyinstaller

# Alias: 'make build' defaults to nuitka
build: build-nuitka

# ── Dev ────────────────────────────────────────────────────────────────────────

# Run the app locally in development mode
run:
	uv run streamlit run main.py

# ── Clean ──────────────────────────────────────────────────────────────────────

# Clean all build artifacts portably using Python
clean:
	uv run python -c "import shutil, glob, os; \
	[shutil.rmtree(d, ignore_errors=True) for d in ['build', 'dist'] if os.path.exists(d)]; \
	[os.remove(f) for f in glob.glob('*.exe')]"
