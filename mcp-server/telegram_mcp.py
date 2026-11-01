"""MCP server that exposes the Telegram companion to MCP clients (Claude Desktop, Cursor, ...).

It uses the same config.json as the bot. Telegram lets only ONE program read a bot's updates,
so this server never polls Telegram itself: recent messages come from the logs the running bot
writes (chat_history.jsonl and sessions/*/chat_history.jsonl), and sending goes through the Bot API.

    python3 mcp-server/telegram_mcp.py
"""
import asyncio
import datetime
import glob
import json
import os
import re
import sys
import urllib.parse
import urllib.request

try:
    import requests
except ImportError:
    requests = None

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError:
        MCPServer = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(PROJECT_ROOT, "memory_summary.txt")
CHAT_LOG_FILE = os.path.join(PROJECT_ROOT, "chat_history.jsonl")
SESSIONS_DIR = os.path.join(PROJECT_ROOT, "sessions")
LOG_FILE = os.path.join(PROJECT_ROOT, "agent.log")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")


def load_cfg() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as cf:
            return json.load(cf)
    except Exception:
        return {}


def master_id() -> int:
    try:
        return int(load_cfg().get("master_id") or 0)
    except (TypeError, ValueError):
        return 0


companion_state = {
    "mood": "happy",
    "status": "Ready and serving user",
    "last_interaction": str(datetime.datetime.now())
}


def tg_api(method: str, params: dict = None, files: dict = None) -> dict:
    """Calls the Telegram Bot API with the bot token and proxy from config.json."""
    cfg = load_cfg()
    token = str(cfg.get("telegram_bot_token") or "").strip()
    if not token:
        return {"ok": False, "description": "telegram_bot_token is not set in config.json"}
    if requests is None:
        return {"ok": False, "description": "the 'requests' package is not installed"}
    base = str(cfg.get("telegram_api_base") or "https://api.telegram.org").rstrip("/")
    proxy = str(cfg.get("telegram_proxy") or "").strip()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    url = f"{base}/bot{token}/{method}"
    body = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        if files:
            form = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in body.items()}
            resp = requests.post(url, data=form, files=files, timeout=60, proxies=proxies)
        else:
            resp = requests.post(url, json=body, timeout=30, proxies=proxies)
        return resp.json()
    except Exception as e:
        return {"ok": False, "description": str(e).replace(token, "<token>")}


if MCPServer is not None:
    app = MCPServer(name="Telegram-Companion")
else:
    class DummyMCP:
        def tool(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def run(self, *args, **kwargs):
            sys.stderr.write("Error: 'mcp' package is not installed. Please run: pip install -r requirements.txt\n")
            sys.exit(1)
    app = DummyMCP()


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


@app.tool(name="tg_send_master_msg", description="Send a Telegram message to the Master (the owner set as master_id).")
def tg_send_master_msg(message: str) -> str:
    """Send a message to the Master."""
    if master_id() <= 0:
        return _dump({"ok": False, "description": "master_id is not set in config.json"})
    return _dump(tg_api("sendMessage", {"chat_id": master_id(), "text": message}))


@app.tool(name="tg_send_message", description="Send a Telegram message to any chat the bot can write to (user ID or group chat ID).")
def tg_send_message(chat_id: int, message: str) -> str:
    """Send a message to a chat."""
    return _dump(tg_api("sendMessage", {"chat_id": chat_id, "text": message}))


@app.tool(name="tg_send_image", description="Send a picture (local file path or http(s) URL) to the Master or another chat.")
def tg_send_image(image_path: str, chat_id: int = 0) -> str:
    """Send a picture."""
    target = chat_id or master_id()
    if image_path.startswith(("http://", "https://")):
        return _dump(tg_api("sendPhoto", {"chat_id": target, "photo": image_path}))
    path = os.path.expanduser(image_path)
    if not os.path.isfile(path):
        return _dump({"ok": False, "description": f"file not found: {image_path}"})
    with open(path, "rb") as f:
        data = f.read()
    method, field = ("sendAnimation", "animation") if path.lower().endswith(".gif") else ("sendPhoto", "photo")
    return _dump(tg_api(method, {"chat_id": target}, files={field: (os.path.basename(path), data)}))


@app.tool(name="tg_get_me", description="Get the bot account details (ID, username, name).")
def tg_get_me() -> str:
    """Bot account details."""
    return _dump(tg_api("getMe"))


@app.tool(name="tg_get_chat", description="Get details about a chat (user ID or group chat ID) the bot knows.")
def tg_get_chat(chat_id: int) -> str:
    """Chat details."""
    return _dump(tg_api("getChat", {"chat_id": chat_id}))


@app.tool(name="tg_delete_msg", description="Delete a message the bot sent (chat ID + message ID).")
def tg_delete_msg(chat_id: int, message_id: int) -> str:
    """Delete a message."""
    return _dump(tg_api("deleteMessage", {"chat_id": chat_id, "message_id": message_id}))


def _log_files(chat: str) -> list:
    """chat: "master" (default), "all", or a session folder such as group_-1001234 / private_5678."""
    chat = (chat or "master").strip()
    if chat == "master":
        return [("master", CHAT_LOG_FILE)]
    if chat == "all":
        out = [("master", CHAT_LOG_FILE)]
        for p in sorted(glob.glob(os.path.join(SESSIONS_DIR, "*", "chat_history.jsonl"))):
            out.append((os.path.basename(os.path.dirname(p)), p))
        return out
    safe = re.sub(r"[^\w\-]", "", chat)
    return [(safe, os.path.join(SESSIONS_DIR, safe, "chat_history.jsonl"))]


@app.tool(name="tg_get_recent_messages",
          description="Recent messages from the bot's chat logs. chat: 'master' (default), 'all', or a session such as 'group_-1001234567890' or 'private_5678'.")
def tg_get_recent_messages(limit: int = 10, chat: str = "master") -> str:
    """Latest logged messages."""
    entries = []
    for name, path in _log_files(chat):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f.readlines()[-max(1, limit) * 3:]:
                    try:
                        e = json.loads(line)
                        e["chat"] = name
                        entries.append(e)
                    except Exception:
                        continue
        except Exception as e:
            return _dump({"status": "error", "message": str(e)})
    entries.sort(key=lambda e: e.get("time", ""))
    entries = entries[-max(1, limit):]
    return _dump({"count": len(entries), "messages": entries})


@app.tool(name="set_companion_status", description="Updates the companion's internal mood and activity status.")
def set_companion_status(mood: str, status_text: str) -> str:
    """Update companion internal status."""
    companion_state["mood"] = mood
    companion_state["status"] = status_text
    companion_state["last_interaction"] = str(datetime.datetime.now())
    return _dump({"status": "updated", "companion_state": companion_state})


@app.tool(name="web_search", description="Search the live internet for recent news, facts, weather, and reference knowledge.")
def web_search(query: str, max_results: int = 4) -> str:
    """Live web search using ddgs with a Wikipedia fallback."""
    clean_q = query.strip()
    if not clean_q:
        return _dump({"status": "error", "message": "Query cannot be empty"})
    try:
        from ddgs import DDGS
        results = list(DDGS().text(clean_q, max_results=max_results))
        if results:
            return _dump({"status": "ok", "query": clean_q, "results": results})
    except Exception:
        pass
    try:
        encoded_q = urllib.parse.quote(clean_q)
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_q}&format=json&utf8="
        req = urllib.request.Request(wiki_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = data.get("query", {}).get("search", [])
        results = [{"title": it.get("title"), "snippet": re.sub(r"<[^>]+>", "", it.get("snippet", ""))} for it in items[:max_results]]
        return _dump({"status": "ok", "query": clean_q, "results": results})
    except Exception as e:
        return _dump({"status": "error", "message": f"Search failed: {e}"})


@app.tool(name="search_chat_history",
          description="Searches the Master's full chat log for past conversations, topics discussed earlier, or mentions.")
def search_chat_history(query: str, max_results: int = 8) -> str:
    """Search the persistent chat log."""
    clean_q = query.strip()
    if not clean_q:
        return _dump({"status": "error", "message": "Query cannot be empty"})
    matches = []
    if os.path.exists(CHAT_LOG_FILE):
        try:
            with open(CHAT_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if clean_q.lower() in str(item.get("text", "")).lower():
                    ctx = []
                    for c_idx in range(max(0, i - 1), min(len(lines), i + 2)):
                        try:
                            ctx.append(json.loads(lines[c_idx]))
                        except Exception:
                            pass
                    matches.append(ctx)
                    if len(matches) >= max_results:
                        break
        except Exception as e:
            return _dump({"status": "error", "message": str(e)})
    return _dump({"status": "ok", "query": clean_q, "matches": matches})


@app.tool(name="read_memory", description="Reads the full long-term memory archive file (memory_summary.txt).")
def read_memory() -> str:
    """Read the long-term memory."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8-sig") as f:
                return _dump({"status": "ok", "content": f.read().strip()})
        except Exception as e:
            return _dump({"status": "error", "message": str(e)})
    return _dump({"status": "ok", "content": ""})


@app.tool(name="update_memory",
          description="Appends an important fact, preference, habit, or agreement to the long-term memory file.")
def update_memory(content: str) -> str:
    """Append a fact to the long-term memory (the running bot reloads it on restart)."""
    clean_c = content.strip()
    if not clean_c:
        return _dump({"status": "error", "message": "Content cannot be empty"})
    new_line = f"- [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] {clean_c}"
    try:
        existing = ""
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8-sig") as f:
                existing = f.read().strip()
        updated = f"{existing}\n{new_line}" if existing else f"【Long-Term Memory Archive】\n{new_line}"
        tmp = MEMORY_FILE + f".tmp-{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(updated)
        os.replace(tmp, MEMORY_FILE)
        return _dump({"status": "ok", "added": new_line})
    except Exception as e:
        return _dump({"status": "error", "message": str(e)})


@app.tool(name="send_voice_to_master", description="Synthesizes speech with Edge-TTS and sends it to the Master as a Telegram voice message.")
def send_voice_to_master(text: str, voice_character: str = "en-US-JennyNeural") -> str:
    """Synthesize a voice message and send it to the Master."""
    if not EDGE_TTS_AVAILABLE:
        return _dump({"status": "error", "message": "edge-tts is not installed"})
    clean_txt = re.sub(r"\[[^\]]+\]", "", text).strip()
    if not clean_txt:
        return _dump({"status": "error", "message": "Text for voice cannot be empty"})
    temp_audio = os.path.join(PROJECT_ROOT, "temp_mcp_reply.mp3")

    async def _synth():
        await edge_tts.Communicate(clean_txt, voice_character).save(temp_audio)

    try:
        asyncio.run(_synth())
        if not os.path.exists(temp_audio):
            return _dump({"status": "error", "message": "Failed to create audio file"})
        with open(temp_audio, "rb") as af:
            data = af.read()
        res = tg_api("sendVoice", {"chat_id": master_id()}, files={"voice": ("voice.mp3", data, "audio/mpeg")})
        return _dump({"status": "ok" if res.get("ok") else "error", "telegram_response": res})
    except Exception as e:
        return _dump({"status": "error", "message": str(e)})
    finally:
        if os.path.exists(temp_audio):
            try:
                os.remove(temp_audio)
            except Exception:
                pass


if __name__ == "__main__":
    app.run(transport="stdio")
