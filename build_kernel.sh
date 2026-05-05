#!/bin/bash
set -e

_install() {
    # Try uv first (local dev), fallback to pip (CI)
    if command -v uv &>/dev/null; then
        uv pip install "$@" -q
    else
        python3 -m pip install "$@" -q
    fi
}

_cleanup() {
    rm -rf build/ dist/ kernel.spec __pycache__
}

echo "[build] Installing pyinstaller..."
_install pyinstaller

echo "[build] Compiling Base-OS kernel..."
python3 -m PyInstaller --onefile --name kernel base_os/os_kernel.py

echo "[build] Moving binary to project root..."
mv dist/kernel .
_cleanup
echo "[build] Done: ./kernel"
