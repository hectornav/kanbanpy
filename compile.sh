#!/bin/bash
# compile.sh - Compile Kanbanpy Pro v2.0 into a single executable

echo "🚀 Compilando Kanbanpy Pro v2.0..."

# Create virtual env if not exists
if [ ! -d "build_venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv build_venv
fi

source build_venv/bin/activate

echo "📥 Instalando dependencias..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "🛠️ Generando ejecutable con PyInstaller..."
# --noconfirm: overwrite dist/ and build/
# --onefile: single binary
# --windowed: no console window
# --name: binary name
# --paths: include local modules
# --clean: clean cache before building
pyinstaller --noconfirm --onefile --windowed --clean \
    --name kanbanpy_pro_v2 \
    --paths "kanban_app" \
    --hidden-import "PyQt6.QtCore" \
    --hidden-import "PyQt6.QtWidgets" \
    --hidden-import "PyQt6.QtGui" \
    kanban_app/main.py

deactivate

if [ -f "dist/kanbanpy_pro_v2" ]; then
    echo "✅ ¡Listo! Ejecutable creado en: dist/kanbanpy_pro_v2"
    echo "💡 Puedes ejecutarlo con: ./dist/kanbanpy_pro_v2"
else
    echo "❌ Error: No se pudo generar el ejecutable."
fi
