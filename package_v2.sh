#!/bin/bash
# package_v2.sh - Automated build script for Kanbanpy Pro v2.0 (Linux)

echo "--- 📋 Kanbanpy Pro v2.0 Packaging Process ---"

# 1. Setup Virtual Environment
echo "🔹 setting up temporary build environment..."
python3 -m venv build_venv
source build_venv/bin/activate

# 2. Install Dependencies
echo "🔹 installing dependencies (PyQt6, PyInstaller)..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Build the application
echo "🔹 building standalone executable with PyInstaller..."
# --noconfirm: Overwrite existing build
# --onefile: Generate a single binary
# --windowed: No console on launch (for GUI apps)
# --name: Specific name for the binary
# --paths: Ensure local modules are found
pyinstaller --noconfirm --onefile --windowed \
    --name kanbanpy_pro_v2 \
    --paths "kanban_app" \
    --hidden-import "PyQt6.QtCore" \
    --hidden-import "PyQt6.QtWidgets" \
    --hidden-import "PyQt6.QtGui" \
    kanban_app/main.py

# 4. Cleanup and Results
echo "🔹 cleaning up build environment..."
deactivate
rm -rf build_venv

echo ""
echo "--- ✅ BUILD COMPLETE ---"
echo "Binary location: $(pwd)/dist/kanbanpy_pro_v2"
echo "Instructions: Just run './dist/kanbanpy_pro_v2' to start the board."
echo "Note: The database (kanban.db) will be created in the same folder as the executable."
