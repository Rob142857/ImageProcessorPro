# Building Image Processor Pro for macOS

This guide will help you build the Image Processor Pro application on a Mac.

## Prerequisites

1. **Python 3.11 or later**
   - Check if installed: `python3 --version`
   - Download from: https://www.python.org/downloads/

2. **Xcode Command Line Tools** (recommended)
   ```bash
   xcode-select --install
   ```

## Quick Build (Automated)

1. **Transfer the project folder** to your Mac (via USB drive, network share, or git)

2. **Open Terminal** and navigate to the project:
   ```bash
   cd /path/to/ImageProcessorPro
   ```

3. **Make the build script executable:**
   ```bash
   chmod +x build_macos.sh
   ```

4. **Run the build script:**
   ```bash
   ./build_macos.sh
   ```

The script will:
- Create a virtual environment
- Install all dependencies
- Build the .app bundle
- Create a DMG installer (optional)
- Open the dist folder when complete

## Manual Build Steps

If the automated script doesn't work, follow these steps:

### 1. Set up Python environment

```bash
# Navigate to project folder
cd /path/to/ImageProcessorPro

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Build the application

```bash
pyinstaller ImageProcessorPro.spec --noconfirm
```

### 4. Find your application

The built app will be in: `dist/ImageProcessorPro/`

You can run it with:
```bash
open dist/ImageProcessorPro.app
```

## Distribution

### Option 1: Zip the folder (simplest)

```bash
cd dist
zip -r ImageProcessorPro-macOS.zip ImageProcessorPro
```

Transfer the ZIP file to other Macs. Users just unzip and double-click the .app

### Option 2: Create a DMG installer (recommended)

```bash
hdiutil create -volname "ImageProcessorPro" \
  -srcfolder dist/ImageProcessorPro.app \
  -ov -format UDZO \
  dist/ImageProcessorPro-Installer.dmg
```

The DMG file is a professional installer that macOS users expect.

## Troubleshooting

### "Permission denied" error
```bash
chmod +x build_macos.sh
```

### Python not found
Install Python 3 from https://www.python.org/downloads/

### Module import errors
Make sure you activated the virtual environment:
```bash
source .venv/bin/activate
```

### "App is damaged" warning on other Macs
This happens because the app isn't code-signed. Users can bypass with:
```bash
xattr -cr /path/to/ImageProcessorPro.app
```

Or right-click → Open (instead of double-clicking)

### Font issues
The app uses system fonts. If watermarks don't appear, check that these exist:
- `/System/Library/Fonts/Helvetica.ttc`
- `/Library/Fonts/Arial.ttf`

## Code Signing (Optional - For Distribution)

If you have an Apple Developer account ($99/year), you can sign the app:

```bash
# Sign the app
codesign --deep --force --sign "Developer ID Application: Your Name" \
  dist/ImageProcessorPro.app

# Verify signature
codesign --verify --deep --strict --verbose=2 \
  dist/ImageProcessorPro.app

# Notarize with Apple (required for macOS 10.15+)
xcrun notarytool submit dist/ImageProcessorPro-Installer.dmg \
  --apple-id your@email.com \
  --team-id TEAMID \
  --password app-specific-password
```

## System Requirements

- macOS 10.13 (High Sierra) or later
- 100 MB free disk space
- Python 3.11+ (for building only)

## Testing the App

After building, test these features:
1. Launch the app (double-click)
2. Select an input folder with images
3. Click "Start Processing"
4. Check progress bar updates
5. Verify watermarked images in output folder

## Questions?

The app was built with:
- Python 3.11
- Pillow (PIL) for image processing
- CustomTkinter for modern GUI
- PyInstaller for packaging

For issues, check the logs in: `logs/image_processor_*.log`
