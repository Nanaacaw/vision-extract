@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%\frontend"

if "%OCR_BACKEND_URL%"=="" set "OCR_BACKEND_URL=http://localhost:8001"
if "%OCR_FRONTEND_PORT%"=="" set "OCR_FRONTEND_PORT=3000"

echo Starting Finance OCR frontend...
echo URL: http://localhost:%OCR_FRONTEND_PORT%
echo Backend: %OCR_BACKEND_URL%
echo.

if not exist ".\node_modules" (
    echo Missing frontend dependencies.
    echo Run: cd frontend ^&^& npm install
    exit /b 1
)

npm run dev -- --port %OCR_FRONTEND_PORT%
