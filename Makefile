BACKEND_PORT ?= 8001
FRONTEND_PORT ?= 3000
PYTHON ?= .\venv\Scripts\python.exe

.PHONY: help install frontend-install backend frontend dev check clean

help:
	@echo Finance OCR commands
	@echo.
	@echo   make backend   Start FastAPI backend on localhost:$(BACKEND_PORT)
	@echo   make frontend  Start Next.js frontend on localhost:$(FRONTEND_PORT)
	@echo   make dev       Start backend and frontend in separate windows
	@echo   make check     Run backend compile check
	@echo   make clean     Remove runtime logs

install:
	@cmd /c "$(PYTHON) -m pip install -r requirements.txt"

frontend-install:
	@cmd /c "cd frontend && npm install"

backend:
	@cmd /c "set OCR_BACKEND_PORT=$(BACKEND_PORT)&& $(PYTHON) main.py"

frontend:
	@cmd /c "cd frontend && set OCR_BACKEND_URL=http://localhost:$(BACKEND_PORT)&& npm run dev -- --port $(FRONTEND_PORT)"

dev:
	@cmd /c "set OCR_BACKEND_PORT=$(BACKEND_PORT)&& set OCR_FRONTEND_PORT=$(FRONTEND_PORT)&& scripts\start-all.bat"

check:
	@cmd /c "$(PYTHON) -m py_compile main.py"
	@cmd /c "$(PYTHON) -m py_compile api\routes.py ocr_engine\ocr.py ocr_engine\document.py"
	@cmd /c "cd frontend && npm run typecheck"

clean:
	@cmd /c "powershell -NoProfile -Command ""Remove-Item -Force *.log,*.err -ErrorAction SilentlyContinue"""
