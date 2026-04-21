BACKEND_PORT ?= 8001
PYTHON ?= .\venv\Scripts\python.exe

.PHONY: help install backend dev check clean

help:
	@echo Finance OCR commands
	@echo.
	@echo   make backend   Start FastAPI backend on localhost:$(BACKEND_PORT)
	@echo   make dev       Start backend in a separate window
	@echo   make check     Run backend compile check
	@echo   make clean     Remove runtime logs

install:
	@cmd /c "$(PYTHON) -m pip install -r requirements.txt"

backend:
	@cmd /c "set OCR_BACKEND_PORT=$(BACKEND_PORT)&& $(PYTHON) main.py"

dev:
	@cmd /c "set OCR_BACKEND_PORT=$(BACKEND_PORT)&& start-dev.bat"

check:
	@cmd /c "$(PYTHON) -m py_compile main.py"
	@cmd /c "$(PYTHON) -m py_compile api\routes.py ocr_engine\ocr.py ocr_engine\document.py"

clean:
	@cmd /c "powershell -NoProfile -Command ""Remove-Item -Force *.log,*.err -ErrorAction SilentlyContinue"""
