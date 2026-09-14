# Makefile for TicketRadar

.PHONY: install build build-pyinstaller build-nuitka build-ui run ui clean deploy nginx-setup nginx-reload nginx-cert-renew

# Default target
all: run

# Install all dependencies using uv and npm
install:
	cd src/Backend && uv sync
	cd src/UI && npm install

# ── Build targets ──────────────────────────────────────────────────────────────

# Build only the frontend UI
build-ui:
	cd src/UI && npm run build

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

# ── Deployment ─────────────────────────────────────────────────────────────────

# Deploy to FastAPI Cloud
deploy:
	cd src/Backend && uv run fastapi deploy

# ── Nginx & SSL (Host Machine) ─────────────────────────────────────────────────

# Install Nginx, configure reverse proxy for api.ticketradar.darkglance.in, and obtain Let's Encrypt SSL
nginx-setup:
	@chmod +x nginx/setup.sh
	@bash nginx/setup.sh

# Test and reload Nginx configuration
nginx-reload:
	@sudo nginx -t && sudo systemctl reload nginx

# Test Let's Encrypt automated certificate renewal
nginx-cert-renew:
	@sudo certbot renew --dry-run

# ── Dev ────────────────────────────────────────────────────────────────────────

# Run only the frontend UI dev server
ui:
	cd src/UI && npm run dev

# Run the app locally in development mode (starts both Vite dev server and FastAPI)
run:
	@echo Starting FastAPI backend...
	cd src/Backend && uv run python main.py
	

# ── Clean ──────────────────────────────────────────────────────────────────────

# Clean all build artifacts, virtual environments, node_modules, dist, and pycache
clean:
	@echo Cleaning build artifacts, venv, node_modules, dist, and pycache...
	@python -c "import os, shutil; \
	[shutil.rmtree(os.path.join(r, d), ignore_errors=True) for r, ds, fs in os.walk('.', topdown=True) for d in list(ds) if d in ('build', 'dist', 'node_modules', '.venv', 'venv', '__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache') or d.endswith(('.build', '.dist', '.onefile-build', '.egg-info'))]; \
	[os.remove(os.path.join(r, f)) for r, ds, fs in os.walk('.') for f in fs if f.endswith(('.pyc', '.pyo', '.pyd', '.exe'))]"

