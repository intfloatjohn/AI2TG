#!/usr/bin/env bash
# ==============================================================================
# Telegram AI Companion - All-in-One Setup (Linux / macOS)
# Sets up the Python venv, pre-caches the TTS voice, checks web search,
# creates config.json and checks that Telegram can be reached.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================="
echo "   Telegram AI Companion - All-in-One Setup              "
echo "========================================================="
echo ""

# 1. System packages (Debian/Ubuntu). ffmpeg is needed for voice messages.
if command -v apt-get &> /dev/null; then
    MISSING_PKGS=""
    for pkg in python3 python3-pip python3-venv ffmpeg curl; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            MISSING_PKGS="$MISSING_PKGS $pkg"
        fi
    done
    if [ -n "$MISSING_PKGS" ]; then
        echo "[*] Installing required system packages:$MISSING_PKGS..."
        if command -v sudo &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y $MISSING_PKGS
        else
            apt-get update && apt-get install -y $MISSING_PKGS
        fi
    fi
elif ! command -v ffmpeg &> /dev/null; then
    echo "[!] ffmpeg was not found. Voice messages need it (macOS: brew install ffmpeg)."
fi

# 2. Python environment
echo ""
echo "=== [1/4] Setting up Python Environment & Dependencies ==="
source "$SCRIPT_DIR/ensure_venv.sh"
ensure_venv "$SCRIPT_DIR"
echo "[*] Installing / upgrading Python dependencies..."
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt

# 3. Pre-cache the TTS voice
echo ""
echo "=== [2/4] Initializing TTS Voice Engine ==="
"$VENV_PY" -c "
import asyncio, os
try:
    import edge_tts
    async def init_voice():
        await edge_tts.Communicate('Voice engine ready.', 'en-US-JennyNeural').save('test_tts.mp3')
    asyncio.run(init_voice())
    if os.path.exists('test_tts.mp3') and os.path.getsize('test_tts.mp3') > 100:
        os.remove('test_tts.mp3')
        print('[+] Voice engine ready.')
    else:
        print('[!] Voice synthesis returned empty output.')
except Exception as e:
    print(f'[*] TTS notice: {e} (voice is synthesized on demand)')
"

# 4. Web search
echo ""
echo "=== [3/4] Verifying Live Web Search ==="
"$VENV_PY" -c "
try:
    from ddgs import DDGS
    res = list(DDGS(timeout=5).text('Python', max_results=1))
    print('[+] Web search works.' if res else '[+] Web search online.')
except Exception as e:
    print(f'[*] Web search notice: {e} (Bing fallback enabled)')
"

# 5. config.json
echo ""
echo "=== [4/4] Configuration ==="
if [ ! -f "config.json" ]; then
    echo "[*] config.json not found. Creating it from config.example.json..."
    cp config.example.json config.json
    if [ -t 0 ]; then
        echo ""
        echo "Answer a few questions (press Enter to skip and edit config.json later):"
        read -r -p "  Telegram bot token from @BotFather: " TG_TOKEN
        read -r -p "  Model API key (OpenRouter / OpenAI-compatible): " API_KEY
        read -r -p "  Your Telegram user ID (empty = find it in the log later): " MASTER_ID
        read -r -p "  Proxy for Telegram, if Telegram is blocked here (e.g. http://127.0.0.1:7890): " TG_PROXY
        TG_TOKEN="$TG_TOKEN" API_KEY="$API_KEY" MASTER_ID="$MASTER_ID" TG_PROXY="$TG_PROXY" "$VENV_PY" -c "
import json, os
with open('config.json', encoding='utf-8') as f:
    cfg = json.load(f)
if os.environ.get('TG_TOKEN', '').strip():
    cfg['telegram_bot_token'] = os.environ['TG_TOKEN'].strip()
if os.environ.get('API_KEY', '').strip():
    cfg['api_key'] = os.environ['API_KEY'].strip()
if os.environ.get('MASTER_ID', '').strip().isdigit():
    cfg['master_id'] = int(os.environ['MASTER_ID'].strip())
if os.environ.get('TG_PROXY', '').strip():
    cfg['telegram_proxy'] = os.environ['TG_PROXY'].strip()
with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print('[+] config.json saved.')
"
    else
        echo "[!] Edit config.json: telegram_bot_token, api_key and master_id."
    fi
fi

# Check that the token works and Telegram is reachable (through telegram_proxy if set)
"$VENV_PY" -c "
import json, requests
cfg = json.load(open('config.json', encoding='utf-8-sig'))
token = str(cfg.get('telegram_bot_token') or '').strip()
if not token or 'YOUR_BOT_TOKEN' in token:
    print('[!] telegram_bot_token is not set yet in config.json.')
    raise SystemExit(0)
proxy = str(cfg.get('telegram_proxy') or '').strip()
base = str(cfg.get('telegram_api_base') or 'https://api.telegram.org').rstrip('/')
try:
    r = requests.get(f'{base}/bot{token}/getMe', timeout=10, proxies={'http': proxy, 'https': proxy} if proxy else None).json()
    if r.get('ok'):
        print('[+] Telegram OK: the bot is @' + r['result'].get('username', '?'))
    else:
        print('[!] Telegram refused the token: ' + str(r.get('description')))
except Exception as e:
    print('[!] Could not reach Telegram (' + type(e).__name__ + '). If it is blocked on this network, set telegram_proxy in config.json.')
" || true

echo ""
echo "========================================================="
echo " [✓] Setup complete                                      "
echo "========================================================="
echo " Start the companion any time with:  ./start.sh"
echo " Then send your bot a message in Telegram (press Start)."
echo ""

if [ -t 0 ]; then
    read -r -p "Start the companion now? [Y/n]: " run_now
    run_now=${run_now:-Y}
    if [[ "$run_now" =~ ^[Yy]$ ]]; then
        exec ./start.sh
    fi
fi
