#!/bin/bash
set -e
uv venv .venv
echo "[build] Installing pyinstaller..."
uv pip install pyinstaller -q 2>/dev/null || uv pip install pyinstaller -q
echo "[build] Compiling Base-OS kernel..."
pyinstaller --onefile --name kernel base_os/os_kernel.py
echo "[build] Moving binary to project root..."
mv dist/kernel .
rm -rf build/ dist/ kernel.spec
echo "[build] Done: ./kernel"
