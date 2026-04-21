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
if "%OCR_FRONTEND_PORT%"=="" set "OCR_FRONTEND_PORT=3001"
if "%OCR_BACKEND_URL%"=="" set "OCR_BACKEND_URL=http://localhost:%OCR_BACKEND_PORT%"

echo Starting Finance OCR stack...
echo Backend:  http://localhost:%OCR_BACKEND_PORT%
echo Frontend: http://localhost:%OCR_FRONTEND_PORT%
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo Missing .\venv\Scripts\python.exe
    echo Run setup.bat or create the Python virtual environment first.
    exit /b 1
)

if not exist ".\frontend\node_modules" (
    echo Missing frontend dependencies.
    echo Run: cd frontend ^&^& npm install
    exit /b 1
)

start "Finance OCR Backend" cmd /k ""%ROOT%\scripts\start-backend.bat""
start "Finance OCR Frontend" cmd /k ""%ROOT%\scripts\start-frontend.bat""

echo Started both services in separate terminal windows.
