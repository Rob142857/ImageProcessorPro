#!/bin/bash
# ============================================
#  Build Image Processor Pro for macOS
#  Creates a portable .app bundle
# ============================================

echo ""
echo "============================================"
echo "  Image Processor Pro - macOS Build"
echo "============================================"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3 from https://www.python.org/"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install/upgrade PyInstaller
echo ""
echo "Installing PyInstaller..."
pip install pyinstaller --upgrade

# Run the build
echo ""
echo "Building application..."
pyinstaller ImageProcessorPro.spec --noconfirm

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "  BUILD SUCCESSFUL!"
    echo "============================================"
    echo ""
    echo "Output location: dist/ImageProcessorPro/"
    echo ""
    echo "To run the app:"
    echo "  open dist/ImageProcessorPro.app"
    echo "  OR"
    echo "  dist/ImageProcessorPro/ImageProcessorPro"
    echo ""
    echo "To distribute:"
    echo "  1. Zip the entire 'dist/ImageProcessorPro' folder, OR"
    echo "  2. Create a DMG (optional, see below)"
    echo ""
    
    # Optional: Create a DMG if app bundle exists
    if [ -d "dist/ImageProcessorPro.app" ]; then
        echo "Creating DMG installer..."
        if command -v hdiutil &> /dev/null; then
            hdiutil create -volname "ImageProcessorPro" -srcfolder "dist/ImageProcessorPro.app" -ov -format UDZO "dist/ImageProcessorPro-Installer.dmg" 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "✓ DMG created: dist/ImageProcessorPro-Installer.dmg"
            fi
        fi
    fi
    
    # Open the dist folder
    if command -v open &> /dev/null; then
        open dist/
    fi
else
    echo ""
    echo "============================================"
    echo "  BUILD FAILED!"
    echo "============================================"
    echo "Check the error messages above."
    exit 1
fi
