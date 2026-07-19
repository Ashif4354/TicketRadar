# Makefile for TicketRadar

.PHONY: install build run clean

# Default target
all: build

# Install all dependencies using uv
install:
	uv sync

# Build the standalone executable using PyInstaller
build:
	uv run pyinstaller TicketRadar.spec --clean

# Run the app locally in development mode
run:
	uv run streamlit run main.py

# Clean build artifacts portably using Python
clean:
	uv run python -c "import shutil, glob, os; \
	[shutil.rmtree(d, ignore_errors=True) for d in ['build', 'dist'] if os.path.exists(d)]; \
	[os.remove(f) for f in glob.glob('*.exe')]"
