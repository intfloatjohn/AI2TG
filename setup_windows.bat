@echo off
chcp 65001 >nul
title Telegram AI Companion Setup (Windows)
cd /d "%~dp0"

echo =========================================================
echo       Telegram AI Companion - All-in-One Setup (Windows)
echo =========================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please download and install Python 3.10+ from https://www.python.org/
    echo (Make sure to check "Add python.exe to PATH" during installation)
    pause
    exit /b 1
)

:: 2. Setup venv
if not exist "venv" (
    echo [*] Creating Python virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

echo [*] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Pre-cache TTS Voice Engine
echo.
echo [*] Initializing Edge-TTS voice engine...
python -c "import edge_tts, asyncio, os; asyncio.run(edge_tts.Communicate('Voice engine ready.', 'en-US-JennyNeural').save('test_tts.mp3')); os.remove('test_tts.mp3') if os.path.exists('test_tts.mp3') else None; print('[+] Voice engine ready!')"

:: ffmpeg is needed for voice messages
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] ffmpeg was not found. Voice messages need it:
    echo     winget install Gyan.FFmpeg   ^(then open a new window^)
)

:: 3. Check config.json
if not exist "config.json" (
    echo.
    echo [*] config.json not found. Creating it from config.example.json...
    copy config.example.json config.json >nul
    echo.
    echo [!] Created config.json. Open it and fill in:
    echo     telegram_bot_token  ^(from @BotFather in Telegram^)
    echo     api_key             ^(your model API key^)
    echo     master_id           ^(your Telegram user ID; the bot's log shows it when you message the bot^)
    echo.
    notepad config.json
)

echo.
echo =========================================================
echo Setup completed! Starting the Telegram AI Companion...
echo (Press Ctrl+C in this window to stop it)
echo =========================================================
echo.

python autonomous_agent.py

pause
