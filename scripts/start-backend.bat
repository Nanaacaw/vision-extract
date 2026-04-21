@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

if exist "%ROOT%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in (`findstr /r /v "^[ ]*# ^[ ]*$" "%ROOT%\.env"`) do (
        if not defined %%A set "%%A=%%B"
    )
)

if "%OCR_BACKEND_PORT%"=="" set "OCR_BACKEND_PORT=8001"

echo Starting Finance OCR backend...
echo URL: http://localhost:%OCR_BACKEND_PORT%
echo Docs: http://localhost:%OCR_BACKEND_PORT%/docs
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo Missing .\venv\Scripts\python.exe
    echo Run setup.bat or create the Python virtual environment first.
    exit /b 1
)

".\venv\Scripts\python.exe" main.py
