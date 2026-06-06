#!/bin/bash
# FUTMANAGER — macOS .app builder (GUI nativa Tkinter)
# PyInstaller (BUNDLE) gera dist/FutManager.app windowed direto.
set -e

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"

echo "📦 Build FutManager.app (GUI Tkinter) ..."
rm -rf build dist/FutManager.app dist/futmanager
python3 -m PyInstaller futmanager.spec --noconfirm

APP="dist/FutManager.app"
if [ -d "$APP" ]; then
    echo "✅ $APP criado"
    du -sh "$APP" | awk '{print "   Tamanho:", $1}'
    echo ""
    echo "Testar:  open '$APP'"
else
    echo "❌ Build falhou — $APP não encontrado"
    exit 1
fi
