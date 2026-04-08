@echo off
REM OCR AI - Finance Edition Setup Script for Windows

echo ========================================
echo OCR AI - Finance Edition - Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Python found!
echo.

REM Create virtual environment
echo [2/3] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [3/3] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To start the application:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: python main.py
echo   3. Open: http://localhost:8000
echo.
echo Features:
echo   - Auto-detect finance documents
echo   - PDF and image support
echo   - Interactive bounding boxes
echo   - Clean markdown formatting
echo.
pause
