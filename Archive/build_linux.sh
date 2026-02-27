#!/bin/bash
# ═══════════════════════════════════════════════════════
#  Red's Garbage Game — Linux Build Script
# ═══════════════════════════════════════════════════════
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "══════════════════════════════════════════"
echo "  Building Red's Garbage Game for Linux"
echo "══════════════════════════════════════════"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Install Python 3.8+."
    exit 1
fi

PYTHON=python3
echo "[1/4] Python: $($PYTHON --version)"

# Check/install dependencies
echo "[2/4] Checking dependencies..."

if ! $PYTHON -c "import pygame" 2>/dev/null; then
    echo "  Installing pygame..."
    $PYTHON -m pip install pygame-ce 2>/dev/null || $PYTHON -m pip install pygame
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
$PYTHON -m PyInstaller build_linux.spec \
    --noconfirm \
    --clean \
    2>&1 | tail -20

if [ $? -eq 0 ] && [ -d "dist/RedsGarbageGame" ]; then
    echo ""
    echo "══════════════════════════════════════════"
    echo "  BUILD SUCCESSFUL!"
    echo "══════════════════════════════════════════"
    echo "  Output: dist/RedsGarbageGame/"
    echo "  Run:    ./dist/RedsGarbageGame/RedsGarbageGame"
    echo ""

    # Make executable
    chmod +x dist/RedsGarbageGame/RedsGarbageGame

    # Create a convenience run script
    cat > dist/RedsGarbageGame/run.sh << 'RUNEOF'
#!/bin/bash
cd "$(dirname "$0")"
./RedsGarbageGame "$@"
RUNEOF
    chmod +x dist/RedsGarbageGame/run.sh

    # Tar it up for distribution
    echo "  Creating tarball..."
    cd dist
    tar -czf RedsGarbageGame-linux-x86_64.tar.gz RedsGarbageGame/
    cd ..
    echo "  Archive: dist/RedsGarbageGame-linux-x86_64.tar.gz"
    echo ""

    # Show size
    du -sh dist/RedsGarbageGame-linux-x86_64.tar.gz
    du -sh dist/RedsGarbageGame/
else
    echo ""
    echo "[ERROR] Build failed. Check output above."
    exit 1
fi