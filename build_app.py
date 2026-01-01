"""
Build script for Image Processor Pro
Creates portable executables for Windows and macOS using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

APP_NAME = "ImageProcessorPro"
VERSION = "1.0.0"

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_windows():
    """Build Windows executable."""
    print("\n" + "="*50)
    print("Building Windows Executable...")
    print("="*50 + "\n")
    
    # PyInstaller command for Windows
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onedir",  # Create a folder with exe and dependencies (more reliable)
        "--windowed",  # No console window
        "--icon", "assets/icon.ico" if os.path.exists("assets/icon.ico") else "NONE",
        "--add-data", "config;config",  # Include config folder
        "--add-data", "src;src",  # Include src folder
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "customtkinter",
        "--collect-all", "customtkinter",
        "--collect-all", "PIL",
        "--noconfirm",
        "gui_app.py"
    ]
    
    subprocess.run(cmd, check=True)
    
    # Create distribution folder
    dist_folder = Path("dist") / APP_NAME
    if dist_folder.exists():
        print(f"\n✓ Windows build complete: {dist_folder}")
        print(f"  Run: {dist_folder / (APP_NAME + '.exe')}")

def build_macos():
    """Build macOS application bundle."""
    print("\n" + "="*50)
    print("Building macOS Application...")
    print("="*50 + "\n")
    
    # PyInstaller command for macOS
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onedir",
        "--windowed",
        "--icon", "assets/icon.icns" if os.path.exists("assets/icon.icns") else "NONE",
        "--add-data", "config:config",  # macOS uses : instead of ;
        "--add-data", "src:src",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "customtkinter",
        "--collect-all", "customtkinter",
        "--collect-all", "PIL",
        "--noconfirm",
        "--osx-bundle-identifier", "com.mjwestate.imageprocessorpro",
        "gui_app.py"
    ]
    
    subprocess.run(cmd, check=True)
    
    dist_folder = Path("dist") / APP_NAME
    if dist_folder.exists():
        print(f"\n✓ macOS build complete: {dist_folder}")

def create_portable_zip():
    """Create a portable ZIP distribution."""
    import zipfile
    
    dist_folder = Path("dist") / APP_NAME
    if not dist_folder.exists():
        print("Build folder not found. Run build first.")
        return
    
    zip_name = f"{APP_NAME}-{VERSION}-{'Windows' if sys.platform == 'win32' else 'macOS'}-Portable.zip"
    zip_path = Path("dist") / zip_name
    
    print(f"\nCreating portable ZIP: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in dist_folder.rglob('*'):
            arcname = file.relative_to(dist_folder.parent)
            zipf.write(file, arcname)
    
    print(f"✓ Portable ZIP created: {zip_path}")
    print(f"  Size: {zip_path.stat().st_size / (1024*1024):.1f} MB")

def main():
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           Image Processor Pro - Build Script              ║
║                    Version {VERSION}                          ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Install PyInstaller
    install_pyinstaller()
    
    # Build based on platform
    if sys.platform == "win32":
        build_windows()
    elif sys.platform == "darwin":
        build_macos()
    else:
        print(f"Unsupported platform: {sys.platform}")
        return
    
    # Create portable ZIP
    create_portable_zip()
    
    print("\n" + "="*50)
    print("BUILD COMPLETE!")
    print("="*50)
    print(f"\nDistribution files are in: {Path('dist').absolute()}")

if __name__ == "__main__":
    main()
