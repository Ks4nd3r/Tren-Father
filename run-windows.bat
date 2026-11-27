@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Python environment not found. See README.md for setup instructions.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
