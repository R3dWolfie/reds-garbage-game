#!/bin/bash
# ═══════════════════════════════════════════════════════
#  Red's Garbage Game — macOS Build Script
# ═══════════════════════════════════════════════════════
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "══════════════════════════════════════════"
echo "  Building Red's Garbage Game for macOS"
echo "══════════════════════════════════════════"

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[ERROR] Python not found. Install Python 3.8+."
    exit 1
fi
echo "[1/4] Python: $($PYTHON --version)"

# Check/install dependencies
echo "[2/4] Checking dependencies..."

if ! $PYTHON -c "import pygame" 2>/dev/null; then
    echo "  Installing pygame..."
    $PYTHON -m pip install pygame-ce 2>/dev/null || $PYTHON -m pip install pygame
fi

if ! $PYTHON -c "import numpy" 2>/dev/null; then
    echo "  Installing numpy..."
    $PYTHON -m pip install numpy
fi

if ! $PYTHON -c "import PyInstaller" 2>/dev/null; then
    echo "  Installing PyInstaller..."
    $PYTHON -m pip install pyinstaller
fi

# Clean previous builds
echo "[3/4] Cleaning previous builds..."
rm -rf build/ dist/

# Build
echo "[4/4] Building with PyInstaller..."
$PYTHON -m PyInstaller build_macos.spec \
    --noconfirm \
    --clean \
    2>&1 | tail -20

if [ $? -eq 0 ] && [ -d "dist/RedsGarbageGame" ]; then
    echo ""
    echo "══════════════════════════════════════════"
    echo "  BUILD SUCCESSFUL!"
    echo "══════════════════════════════════════════"

    # Make executable
    chmod +x dist/RedsGarbageGame/RedsGarbageGame

    # Create run script
    cat > dist/RedsGarbageGame/run.sh << 'RUNEOF'
#!/bin/bash
cd "$(dirname "$0")"
./RedsGarbageGame "$@"
RUNEOF
    chmod +x dist/RedsGarbageGame/run.sh

    # Create tar.gz for distribution
    echo "  Creating tarball..."
    cd dist
    tar -czf RedsGarbageGame-macos.tar.gz RedsGarbageGame/
    cd ..
    echo "  Archive: dist/RedsGarbageGame-macos.tar.gz"

    # Show .app bundle if it was created
    if [ -d "dist/Red's Garbage Game.app" ]; then
        echo "  App bundle: dist/Red's Garbage Game.app"
        # Also create a DMG-friendly zip of the .app
        cd dist
        zip -r "RedsGarbageGame-macos-app.zip" "Red's Garbage Game.app"
        cd ..
        echo "  App zip: dist/RedsGarbageGame-macos-app.zip"
    fi

    echo ""
    du -sh dist/RedsGarbageGame-macos.tar.gz
    du -sh dist/RedsGarbageGame/
else
    echo ""
    echo "[ERROR] Build failed. Check output above."
    exit 1
fi
