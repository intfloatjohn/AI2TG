#!/usr/bin/env bash
# ==============================================================================
# Telegram AI Companion - Daily Launcher (Linux / macOS)
# Checks the Python environment and config.json, then runs the bot.
# Ctrl+C stops it cleanly (press twice to force).
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "      Telegram AI Companion - Launcher                            "
echo "=================================================================="

if [ ! -f "config.json" ]; then
    echo "[x] config.json is missing. Run ./setup.sh first (or copy config.example.json to config.json)."
    exit 1
fi

source "$SCRIPT_DIR/ensure_venv.sh"
if ! ensure_venv "$SCRIPT_DIR"; then
    echo "[x] Python environment is not ready; run ./setup.sh first."
    exit 1
fi
if ! "$VENV_PY" -m pip install -q -r requirements.txt; then
    echo "[!] Could not install/update Python dependencies; trying to start anyway."
fi
command -v ffmpeg >/dev/null 2>&1 || echo "[!] ffmpeg not found: voice messages won't work until it is installed."

AGENT_PID=""
cleanup() {
    trap - INT TERM HUP
    if [ -n "$AGENT_PID" ] && kill -0 "$AGENT_PID" 2>/dev/null; then
        echo ""
        echo "[*] Stopping the companion..."
        kill -TERM "$AGENT_PID" 2>/dev/null || true
        wait "$AGENT_PID" 2>/dev/null || true
    fi
    exit 0
}
trap cleanup INT TERM HUP

echo "[*] Starting the companion (Ctrl+C to stop)..."
"$VENV_PY" autonomous_agent.py &
AGENT_PID=$!
wait "$AGENT_PID" 2>/dev/null || true
AGENT_PID=""
