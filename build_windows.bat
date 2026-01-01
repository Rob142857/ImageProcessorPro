@echo off
REM ============================================
REM  Build Image Processor Pro for Windows
REM  Creates a portable executable
REM ============================================

echo.
echo ============================================
echo   Image Processor Pro - Windows Build
echo ============================================
echo.

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo No virtual environment found. Using system Python.
)

REM Install/upgrade PyInstaller
echo.
echo Installing PyInstaller...
pip install pyinstaller --upgrade --quiet

REM Run the build
echo.
echo Building application...
pyinstaller ImageProcessorPro.spec --noconfirm

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   BUILD SUCCESSFUL!
    echo ============================================
    echo.
    echo Output location: dist\ImageProcessorPro\
    echo.
    echo To run the app:
    echo   dist\ImageProcessorPro\ImageProcessorPro.exe
    echo.
    echo To distribute:
    echo   Zip the entire 'dist\ImageProcessorPro' folder
    echo.
    
    REM Open the dist folder
    explorer dist\ImageProcessorPro
) else (
    echo.
    echo ============================================
    echo   BUILD FAILED!
    echo ============================================
    echo Check the error messages above.
)

pause
