# Makefile for TicketRadar

.PHONY: install build build-pyinstaller build-nuitka run clean

# Default target
all: build-nuitka

# Install all dependencies using uv and npm
install:
	cd src/Backend && uv sync
	cd src/UI && npm install

# ── Build targets ──────────────────────────────────────────────────────────────

# Build with Nuitka (standalone, fastest boot — recommended)
build-nuitka:
	cd src/UI && npm run build
	cd src/Backend && uv run python ../../export/nuitka/build.py

# Build with PyInstaller (single onefile exe — portable but slower boot)
build-pyinstaller:
	cd src/UI && npm run build
	cd src/Backend && uv run pyinstaller ../../export/pyinstaller/TicketRadar.spec --clean \
		--distpath ../../dist/pyinstaller \
		--workpath ../../build/pyinstaller

# Alias: 'make build' defaults to nuitka
build: build-nuitka

# ── Dev ────────────────────────────────────────────────────────────────────────

# Run the app locally in development mode (starts both Vite dev server and FastAPI)
run:
	@echo Starting Vite dev server in background...
	start /B cmd /c "cd src/UI && npm run dev"
	@echo Starting FastAPI backend...
	cd src/Backend && uv run python main.py

# ── Clean ──────────────────────────────────────────────────────────────────────

# Clean all build artifacts portably using Python
clean:
	cd src/Backend && uv run python -c "import shutil, glob, os; \
	[shutil.rmtree(d, ignore_errors=True) for d in ['../../build', '../../dist'] if os.path.exists(d)]; \
	shutil.rmtree('../../src/UI/dist', ignore_errors=True); \
	[os.remove(f) for f in glob.glob('../../*.exe')]"
