@echo off
chcp 65001 >nul
title Telegram AI Companion
cd /d "%~dp0"

echo =========================================================
echo       Telegram AI Companion - Starting (Windows)
echo =========================================================
echo.

if not exist "config.json" (
    echo [x] config.json is missing. Run setup_windows.bat first.
    pause
    exit /b 1
)

if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment...
    call venv\Scripts\activate.bat
)

python autonomous_agent.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Process exited with code %errorlevel%.
)

pause
