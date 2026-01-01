# Image Processor Pro - Quick Build Guide

## 🪟 Windows Build (Current System)

Already built! The portable app is ready in:
```
dist\ImageProcessorPro\ImageProcessorPro.exe
```

To rebuild:
```powershell
.\build_windows.bat
```

Or manually:
```powershell
C:\.venv\Scripts\python.exe -m PyInstaller ImageProcessorPro.spec --noconfirm
```

**To distribute:** Zip the entire `dist\ImageProcessorPro` folder

---

## 🍎 Mac Build (Transfer to Mac)

### Method 1: Automated (Recommended)
```bash
chmod +x build_macos.sh
./build_macos.sh
```

### Method 2: Manual
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pyinstaller ImageProcessorPro.spec --noconfirm
```

**Output:** `dist/ImageProcessorPro.app`

**To distribute:** 
- ZIP: `zip -r ImageProcessorPro-macOS.zip dist/ImageProcessorPro`
- DMG: `hdiutil create -volname "ImageProcessorPro" -srcfolder dist/ImageProcessorPro.app -ov -format UDZO dist/ImageProcessorPro-Installer.dmg`

---

## 📦 Files to Transfer to Mac

Copy these files/folders to your Mac:
```
ImageProcessorPro/
├── build_macos.sh          # Build script
├── ImageProcessorPro.spec  # PyInstaller config
├── gui_app.py              # Main app
├── requirements.txt        # Dependencies
├── BUILD_MAC.md           # Full Mac instructions
├── src/                   # Source code
├── config/                # Config files
└── watermarks/           # (optional) Watermark images
```

---

## ✅ Current Status

- ✅ Windows .exe built and tested
- ✅ Progress bar fixed (uses lambda default args)
- ✅ Stop button working (checks flag between files)
- ✅ Proper © symbol in watermark
- ✅ Dense watermark spacing (-0.3 default)
- ✅ No multiprocessing issues (disabled for GUI)
- ✅ All dependencies bundled (cv2, PIL, tqdm, etc.)

---

## 🎨 Watermark Settings

Current defaults:
- **Text:** "© Michael J Wright Estate | All Rights Reserved"
- **Opacity:** 63/255 (~25%)
- **Color:** Grey (128, 128, 128)
- **Spacing:** -0.3 (30% overlap for dense coverage)
- **Font Size:** 0.015 ratio (~36px on 2400px images)
- **Rotation:** -30° diagonal

---

## 📝 Notes

- Progress bar now updates in real-time
- Stop button works (finishes current file, then stops)
- Lambda closure issue fixed with default arguments
- Mac build script auto-creates venv and installs deps
- Both apps are portable (no installation required)
