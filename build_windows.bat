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

REM Use the project virtual environment when available.
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo ERROR: .venv is required for a reproducible build.
    echo Create it with: py -3.13 -m venv .venv
    exit /b 1
)

REM Install the project's pinned GUI and build dependencies, then use the
REM maintained Python build entrypoint. No missing .spec file is required.
echo.
echo Installing locked project dependencies...
python -m pip install -e ".[gui,build]"
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo Building application...
python build_app.py

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
    
) else (
    echo.
    echo ============================================
    echo   BUILD FAILED!
    echo ============================================
    echo Check the error messages above.
    exit /b %ERRORLEVEL%
)
