"""
Enhanced Installation Script for Image Processor Pro
===================================================

This script handles advanced setup including optional dependencies
and system-specific optimizations.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import json

def run_command(command, description=""):
    """Run a command and handle errors."""
    print(f"\n{description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"Error: Python {version.major}.{version.minor} detected")
        print("Python 3.8 or higher is required")
        return False
    
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def install_core_dependencies():
    """Install core dependencies."""
    print("\n" + "="*50)
    print("Installing Core Dependencies")
    print("="*50)
    
    # Upgrade pip first
    run_command("python -m pip install --upgrade pip", 
                "Upgrading pip...")
    
    # Install core requirements
    if not run_command("pip install -r requirements.txt", 
                      "Installing core requirements..."):
        print("Warning: Some core dependencies failed to install")
        return False
    
    return True

def install_optional_dependencies():
    """Install optional dependencies for enhanced features."""
    print("\n" + "="*50)
    print("Installing Optional Dependencies")
    print("="*50)
    
    optional_packages = {
        "flask": "HTTP API server support",
        "azure-storage-blob": "Azure Blob Storage integration", 
        "azure-cognitiveservices-vision-computervision": "Azure Computer Vision",
        "watchdog": "File system monitoring",
        "psutil": "System monitoring",
        "requests": "HTTP client for API calls"
    }
    
    installed = []
    failed = []
    
    for package, description in optional_packages.items():
        print(f"\nInstalling {package} ({description})...")
        if run_command(f"pip install {package}"):
            installed.append(package)
        else:
            failed.append(package)
    
    print(f"\n✓ Successfully installed: {', '.join(installed)}")
    if failed:
        print(f"⚠ Failed to install: {', '.join(failed)}")
    
    return len(failed) == 0

def setup_folders():
    """Create necessary project folders."""
    print("\n" + "="*50)
    print("Setting Up Project Folders")
    print("="*50)
    
    folders = [
        "input",
        "output", 
        "watermarks",
        "logs",
        "config",
        "temp",
        "azure",
        "power_platform/templates"
    ]
    
    for folder in folders:
        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {folder}")

def setup_poppler():
    """Setup Poppler for PDF processing if not already available"""
    print("\n" + "="*50)
    print("Setting Up Poppler for PDF Processing")
    print("="*50)
    
    try:
        # Check if poppler is already available
        subprocess.run(['pdftoppm', '-h'], capture_output=True, check=True)
        print("✓ Poppler is already available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("🔧 Poppler not found, setting up...")
        
        poppler_dir = os.path.join(os.getcwd(), 'poppler', 'poppler-24.08.0', 'Library', 'bin')
        if os.path.exists(poppler_dir):
            # Add to current session PATH
            current_path = os.environ.get('PATH', '')
            if poppler_dir not in current_path:
                os.environ['PATH'] = current_path + os.pathsep + poppler_dir
                print(f"✓ Added Poppler to PATH: {poppler_dir}")
            return True
        else:
            print("⚠️  Poppler binaries not found.")
            print("   Downloading Poppler for Windows...")
            
            # Download Poppler
            download_cmd = '''Invoke-WebRequest -Uri "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip" -OutFile "poppler.zip"'''
            if run_command(download_cmd, "Downloading Poppler..."):
                extract_cmd = 'Expand-Archive -Path "poppler.zip" -DestinationPath "poppler" -Force'
                if run_command(extract_cmd, "Extracting Poppler..."):
                    # Add to PATH
                    poppler_dir = os.path.join(os.getcwd(), 'poppler', 'poppler-24.08.0', 'Library', 'bin')
                    current_path = os.environ.get('PATH', '')
                    os.environ['PATH'] = current_path + os.pathsep + poppler_dir
                    print(f"✓ Poppler installed and added to PATH")
                    
                    # Clean up zip file
                    try:
                        os.remove("poppler.zip")
                        print("✓ Cleaned up installation files")
                    except:
                        pass
                    return True
            
            print("⚠️  Failed to install Poppler. PDF processing may not work.")
            return False

def create_sample_watermark():
    """Create a sample watermark if none exists."""
    watermark_path = Path("watermarks/sample_watermark.png")
    
    if watermark_path.exists():
        print("✓ Sample watermark already exists")
        return True
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        print("Creating sample watermark...")
        
        # Create a simple text watermark
        img = Image.new('RGBA', (400, 120), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font
        try:
            if platform.system() == "Windows":
                font = ImageFont.truetype('arial.ttf', 48)
            else:
                font = ImageFont.truetype('/System/Library/Fonts/Arial.ttf', 48)
        except:
            font = ImageFont.load_default()
        
        # Draw semi-transparent text
        text = 'SAMPLE'
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (400 - text_width) // 2
        y = (120 - text_height) // 2
        
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 180))
        
        # Add a subtle border
        draw.rectangle([x-10, y-10, x+text_width+10, y+text_height+10], 
                      outline=(255, 255, 255, 100), width=2)
        
        # Save the watermark
        img.save(str(watermark_path))
        print(f"✓ Sample watermark created: {watermark_path}")
        return True
        
    except Exception as e:
        print(f"⚠ Failed to create sample watermark: {e}")
        return False

def create_sample_images():
    """Create sample images for testing."""
    print("\n" + "="*50)
    print("Creating Sample Images")
    print("="*50)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        input_folder = Path("input")
        
        # Sample image configurations
        samples = [
            {'name': 'landscape', 'size': (1920, 1080), 'color': '#4A90E2'},
            {'name': 'portrait', 'size': (1080, 1920), 'color': '#7ED321'},
            {'name': 'square', 'size': (1080, 1080), 'color': '#F5A623'},
            {'name': 'small', 'size': (640, 480), 'color': '#D0021B'}
        ]
        
        for sample in samples:
            img = Image.new('RGB', sample['size'], sample['color'])
            draw = ImageDraw.Draw(img)
            
            # Add some visual elements
            width, height = sample['size']
            
            # Background pattern
            for i in range(0, width, 100):
                draw.line([(i, 0), (i, height)], fill=(255, 255, 255, 50), width=1)
            for i in range(0, height, 100):
                draw.line([(0, i), (width, i)], fill=(255, 255, 255, 50), width=1)
            
            # Central circle
            margin = min(width, height) // 4
            draw.ellipse([margin, margin, width-margin, height-margin], 
                        outline='white', width=8)
            
            # Text
            try:
                if platform.system() == "Windows":
                    font = ImageFont.truetype('arial.ttf', min(width, height) // 20)
                else:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            text = f"{sample['name'].upper()}\n{width}x{height}"
            bbox = draw.multiline_textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.multiline_text((x, y), text, font=font, fill='white', 
                               align='center')
            
            # Save image
            output_path = input_folder / f"sample_{sample['name']}.jpg"
            img.save(str(output_path), 'JPEG', quality=95)
            print(f"✓ Created: {output_path}")
            
        return True
        
    except Exception as e:
        print(f"⚠ Failed to create sample images: {e}")
        return False

def check_system_optimization():
    """Check system for performance optimizations."""
    print("\n" + "="*50)
    print("System Optimization Check")
    print("="*50)
    
    try:
        import psutil
        
        # CPU info
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        print(f"✓ CPU cores: {cpu_count}")
        if cpu_freq:
            print(f"✓ CPU frequency: {cpu_freq.current:.0f} MHz")
        
        # Memory info
        memory = psutil.virtual_memory()
        print(f"✓ Total RAM: {memory.total // (1024**3)} GB")
        print(f"✓ Available RAM: {memory.available // (1024**3)} GB")
        
        # Disk info
        disk = psutil.disk_usage('.')
        print(f"✓ Free disk space: {disk.free // (1024**3)} GB")
        
        # Recommendations
        print("\nPerformance Recommendations:")
        if cpu_count >= 8:
            print("✓ Excellent CPU for multiprocessing")
        elif cpu_count >= 4:
            print("✓ Good CPU, multiprocessing will help")
        else:
            print("⚠ Consider disabling multiprocessing for single-core systems")
        
        if memory.total >= 16 * (1024**3):
            print("✓ Excellent RAM for large image processing")
        elif memory.total >= 8 * (1024**3):
            print("✓ Good RAM, suitable for most image processing")
        else:
            print("⚠ Limited RAM, consider processing smaller batches")
        
        return True
        
    except ImportError:
        print("⚠ psutil not available for system monitoring")
        return False

def create_environment_file():
    """Create a .env template file for configuration."""
    env_content = """# Image Processor Pro Environment Configuration
# Copy this file to .env and customize your settings

# Azure Configuration (Optional)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your_account;AccountKey=your_key;EndpointSuffix=core.windows.net
AZURE_CV_SUBSCRIPTION_KEY=your_computer_vision_key
AZURE_CV_ENDPOINT=https://your_region.api.cognitive.microsoft.com/

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=False

# Processing Defaults
DEFAULT_QUALITY=85
DEFAULT_FORMAT=JPEG
DEFAULT_MAX_WIDTH=1920
DEFAULT_MAX_HEIGHT=1080

# Performance Settings
MAX_WORKERS=auto
ENABLE_MULTIPROCESSING=True

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30
"""
    
    env_file = Path(".env.template")
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✓ Created environment template: {env_file}")

def main():
    """Main installation function."""
    print("="*60)
    print("Image Processor Pro - Enhanced Setup")
    print("="*60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_core_dependencies():
        print("\n❌ Core dependency installation failed")
        return False
    
    # Optional dependencies
    install_optional_dependencies()
    
    # Setup project structure
    setup_folders()
    
    # Setup Poppler for PDF processing
    setup_poppler()
    
    # Create sample content
    create_sample_watermark()
    create_sample_images()
    
    # System optimization check
    check_system_optimization()
    
    # Create configuration templates
    create_environment_file()
    
    print("\n" + "="*60)
    print("✓ Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Run 'python gui_app.py' to start the GUI application")
    print("2. Or run 'python cli.py --help' for command-line usage")
    print("3. Check the README.md for detailed documentation")
    print("4. Customize config files for your specific needs")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n❌ Setup encountered errors. Please check the output above.")
        sys.exit(1)
    
    print("\n🎉 Ready to process images!")
    input("\nPress Enter to exit...")
