@echo off
REM Image Processor Setup and Launcher
REM Windows batch script for easy setup and operation

echo ========================================
echo Image Processor Pro - Setup and Launch
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found: 
python --version

REM Add Poppler to PATH if available (for PDF processing)
if exist "poppler\poppler-24.08.0\Library\bin" (
    set "PATH=%PATH%;%cd%\poppler\poppler-24.08.0\Library\bin"
    echo ✓ Added Poppler to PATH for PDF processing
)

REM Run the enhanced setup if this is first run
if not exist "logs" (
    echo.
    echo Running initial setup...
    python enhanced_setup.py
    if errorlevel 1 (
        echo Setup failed. Please check the error messages above.
        pause
        exit /b 1
    )
    echo.
    echo Setup completed successfully!
    echo.
)

echo.
echo ========================================
echo What would you like to do?
echo ========================================
echo.
echo 1. Launch GUI Application (Recommended)
echo 2. Run Command Line Help
echo 3. Process Images with CLI (Quick)
echo 4. Start HTTP API Server
echo 5. View processed images
echo 6. Exit
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" (
    echo.
    echo Launching GUI Application...
    echo.
    echo The GUI will open in a new window.
    echo You can:
    echo - Select input and output folders
    echo - Choose watermark settings  
    echo - Process images with progress tracking
    echo.
    python gui_app.py
) else if "%choice%"=="2" (
    echo.
    echo Command Line Interface Help:
    echo.
    python cli.py --help
    echo.
    echo Example usage:
    echo python cli.py -i "input" -o "output" -w "watermarks/sample_watermark.png"
    echo.
    pause
) else if "%choice%"=="3" (
    echo.
    echo Quick CLI Processing:
    echo.
    echo Processing sample images with web optimization...
    python cli.py -i "input" -o "output" -w "watermarks/sample_watermark.png" --format WEBP --quality 75
    echo.
    echo Check the 'output' folder for processed images!
    pause
) else if "%choice%"=="4" (
    echo.
    echo Starting HTTP API Server...
    echo.
    echo The API will be available at: http://localhost:5000
    echo Press Ctrl+C to stop the server
    echo.
    pause
    python power_platform/power_platform_integration.py
) else if "%choice%"=="5" (
    echo.
    echo Opening output folder...
    start explorer "output"
) else if "%choice%"=="6" (
    echo.
    echo Thank you for using Image Processor Pro!
    echo.
) else (
    echo.
    echo Invalid choice. Please run the script again.
    pause
)

echo.
echo Press any key to exit...
pause >nul
