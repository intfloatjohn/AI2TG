# Telegram AI Companion · User Guide

This project is a lightweight, 24/7 AI companion for Telegram with long-term memory, vision, voice messages, a sticker library it curates itself, multi-bubble typing, document reading, group chats and private chats with other people. This guide covers setup, every feature and every setting.

---

## Table of Contents
1. [Creating the bot & finding your user ID](#1-creating-the-bot--finding-your-user-id)
2. [Persona prompt customization & hot-reload (`persona/`)](#2-persona-prompt-customization--hot-reload-persona)
3. [AutoCompact long-term memory & realtime memory updates](#3-autocompact-long-term-memory--realtime-memory-updates)
4. [Full chat logs & history search (`chat_history.jsonl`)](#4-full-chat-logs--history-search-chat_historyjsonl)
5. [Multi-bubble typing (`[SEP]`) & plain text](#5-multi-bubble-typing-sep--plain-text)
6. [Picture library & stickers (`picture_db/` & `stickers/`)](#6-picture-library--stickers-picture_db--stickers)
7. [Voice: listening and speaking](#7-voice-listening-and-speaking)
8. [What the bot understands in a message](#8-what-the-bot-understands-in-a-message)
9. [Live web search](#9-live-web-search)
10. [Logs, restarts & clean exit](#10-logs-restarts--clean-exit)
11. [MCP server (`mcp-server/telegram_mcp.py`)](#11-mcp-server-mcp-servertelegram_mcppy)
12. [Configuration reference (`config.json`)](#12-configuration-reference-configjson)
13. [Linux server deployment (systemd)](#13-linux-server-deployment-systemd)
14. [Windows setup & startup](#14-windows-setup--startup)
15. [Group chat](#15-group-chat)
16. [Friend chat](#16-friend-chat)
17. [Coming from AI2QQ](#17-coming-from-ai2qq)

---

## 1. Creating the bot & finding your user ID

1. In Telegram, open **@BotFather**, send `/newbot`, pick a name and a username ending in `bot`. BotFather replies with a **token** like `123456789:AAH...`. Put it in `config.json` as `telegram_bot_token`. Keep it secret: anyone with the token controls the bot.
2. Optional, for groups: in BotFather send `/setprivacy`, choose your bot and **Disable** privacy mode (see [§15.1](#151-enabling)).
3. Start the bot (`./start.sh`), open your bot in Telegram and press **Start** (a bot can't message anyone who never started it).
4. While `master_id` is empty, the log prints a line like:
   ```
   Private message from user ID 123456789 (Your Name (@you)) ignored. If this is you, set "master_id": 123456789 in config.json.
   ```
   Put that number in `config.json` as `master_id`. It is picked up within ~10 seconds, no restart needed (bots like @userinfobot also show your ID).

**Identity is the numeric user ID only.** Names and usernames can be changed by anyone at any time, so they are never used to decide who the Master is.

**Telegram blocked on your network?** Set `telegram_proxy`, e.g. `"http://127.0.0.1:7890"` or `"socks5h://127.0.0.1:1080"` (SOCKS support comes from `PySocks`, already in `requirements.txt`). Only Telegram traffic uses this proxy.

**Only one copy per token.** Telegram delivers a bot's updates to one reader. If two copies run with the same token, the log shows `409 Conflict`; stop one of them. If the bot had a webhook set (for example by another framework), it is removed at startup so long polling works.

---

## 2. Persona prompt customization & hot-reload (`persona/`)

All files that shape the companion's character live in **`persona/`**. They are re-read on every reply, so edits take effect on the next message without a restart.

| File | Purpose |
| :--- | :--- |
| **`persona/system_prompt.md`** | **The main system prompt** the bot loads: personality, plain-text rules, tool tags. |
| **`persona/system_prompt_group.md`** | Chat style in groups (shorter replies, no flooding, …). The safety rules for groups are built into the program and can't be weakened here. |
| `persona/persona.md` | A character sheet template (name, looks, personality). Reference only: copy what you want into `system_prompt.md`. |
| `persona/tools.md` | Reference of every action tag and tool. |

Files named `system_prompt_en.md` / `system_prompt_group_en.md` (from older setups) are used when the plain names are missing.

`single_message_limit_hint` in `config.json` is appended to the prompt as a soft guide for reply length.

---

## 3. AutoCompact long-term memory & realtime memory updates

### Memory layers
1. **Short-term context** (`history.json`): recent turns for continuity.
2. **Realtime memory updates**: when the companion learns something worth keeping, or you say "remember that…", the model writes `[remember: …]`. The fact is appended right away, with a date, to `memory_summary.txt`.
3. **Reading memory**: the model can open the whole archive with `[read_memory]`.
4. **AutoCompact**: when the conversation reaches `compact_threshold` turns (default 30), a background call extracts only **new** facts from the older turns and appends them, keeping the latest `compact_keep_recent` (12) turns as context. Existing memory is never rewritten here; if the call fails, the old turns are kept for next time. Answers cut off by "thinking" models are retried with a bigger budget.
5. **Tidying and backups**: when memory grows past `memory_max_chars` (8000; `group_memory_max_chars` 3000 for each group/person; `public_memory_max_chars` 8000 for the shared memory), the model merges duplicate and outdated entries. The old file is copied to `memory_backups/` first (last 30 kept), and a result that looks cut off or lost too much is rejected.

Duplicates are skipped only when a fact adds nothing; corrections ("Wednesday" → "Thursday", "likes" → "doesn't like") are always saved.

### Managing memory
* **Inspect / edit**: open `memory_summary.txt`.
* **Reset**: empty `memory_summary.txt` and set `history.json` to `[]`.
* **Restore**: stop the bot, copy a file from `memory_backups/` back to `memory_summary.txt`.

---

## 4. Full chat logs & history search (`chat_history.jsonl`)

Every message and reply is appended to `chat_history.jsonl` with a timestamp, so nothing is lost when old turns leave the context. The companion searches it with `[search_history: keyword]` (or the `search_chat_history` tool) and gets matching lines with the lines around them. In the Master's private chat it also searches the recent `agent.log`.

---

## 5. Multi-bubble typing (`[SEP]`) & plain text

* The model can split a reply into several Telegram messages with `[SEP]`: `Sure![SEP]Let me grab some water first[SEP]Give me three minutes~`. Replies split by blank lines are sent as separate bubbles too (not when they contain code, tables or lists). They are sent one after another, `multi_bubble_delay_sec` apart, with "typing…" shown in between (`show_typing`).
* At most `private_max_bubbles` (4) bubbles in private chat and `group_max_bubbles` (3) in groups; extra parts are merged into the last one. Messages longer than Telegram's limit are split automatically.
* Replies are sent as **plain text** (never parsed as Markdown or HTML), so nothing the model writes can turn into formatting or hidden links. Stray `**bold**`, `# headers`, `*actions*` and acting notes like "(smiles)" are cleaned out.

---

## 6. Picture library & stickers (`picture_db/` & `stickers/`)

### 6.1 Your own stickers (`stickers/`)
Put `.jpg`, `.png`, `.gif` or `.webp` files in `stickers/` with short names (`heart.jpg`, `wave.webp`, `sleep.gif`). The model sends one with `[sticker: heart]`. `.webp` files go out as Telegram stickers, `.gif` as GIFs, the rest as photos. See `stickers/STICKERS_GUIDE.md`.

### 6.2 The picture library (`picture_db/`)
The companion keeps its own library (`picture_db/catalog.json` + `picture_db/images/`) and manages it itself:
* **Automatic saving** (Master's private chat): photos you send are saved as private pictures; stickers and GIFs as public ones.
* **Telegram stickers and GIFs are remembered with their Telegram file ID**, so `[PICTURE: …]` sends back the real sticker or GIF, animated ones included.
* **Tags**:
  * Send: `[PICTURE: keyword, tag or ID]`
  * Save the latest picture/sticker/GIF with tags: `[SAVE_STICKER: tag1, tag2: description]`
  * Browse: `[LIST_PICTURES]` or `[LIST_PICTURES: query]`
  * Retag: `[MODIFY_PICTURE: ID or tag: new tags: new description]`
  * Delete: `[DELETE_PICTURE: ID or tag]`
* Saving happens before sending, so a picture saved in a reply can be sent in the same reply.
* Who can see what (groups, friends) is explained in [§15.5](#155-picture-library-stickers-shared-photos-private).

### 6.3 Emoji faces
`[face: hug]`, `[face: laugh]`, `[face: cat]`, … send one emoji as its own message, which Telegram shows large (many are animated). `[emoji: 😂]` sends that emoji. The list of names is `EMOJI_FACES` in `autonomous_agent.py`.

---

## 7. Voice: listening and speaking

**ffmpeg is required** for voice (Debian/Ubuntu: `sudo apt install ffmpeg`; macOS: `brew install ffmpeg`; Windows: `winget install Gyan.FFmpeg`).

### 7.1 Voice messages you send
Telegram voice messages (OGG/Opus) are converted to 16 kHz MP3, then:
1. **Speech-to-text**, if available: a Whisper-compatible API in `asr_api_url` (e.g. OpenAI `https://api.openai.com/v1/audio/transcriptions` with `asr_model` `whisper-1`, or Groq `https://api.groq.com/openai/v1/audio/transcriptions` with `whisper-large-v3`; `asr_api_key`, or the main `api_key` when it is the same host), a local `whisper` install, or Google's free recognizer (`asr_language`, default `en-US`, 3-second limit).
2. Otherwise, **native audio input** for models that can listen (Gemini, GPT-4o audio, Omni): the MP3 is sent as `input_audio`.
3. If neither works, the bot sends a fixed warning (`VOICE IS NOT AVAILABLE`) instead of letting the model guess.

### 7.2 Voice replies
* On demand: the model writes `[voice: text to say]`.
* Every private reply: `"enable_voice_reply": true`.
* Edge-TTS synthesizes the speech (voice: `voice_character`, default `en-US-JennyNeural`; others: `en-US-AriaNeural`, `en-GB-SoniaNeural`, `en-US-GuyNeural`, … see `edge-tts --list-voices`). It is converted to OGG/Opus and sent as a real Telegram voice message with a waveform (as MP3 if ffmpeg can't convert it).

---

## 8. What the bot understands in a message

| Content | What the model gets |
| :--- | :--- |
| Text, captions | the text |
| Photos | the picture (a size up to 1600 px) |
| Image files sent "as file" | the picture |
| Stickers | static: the sticker itself (WEBP converted to PNG for compatibility); animated/video: its preview image; plus the sticker's emoji |
| GIFs | the first-frame preview, labelled `[GIF]` |
| Voice messages | transcript or audio, see [§7](#7-voice-listening-and-speaking) |
| Documents | extracted text from `.txt`, `.md`, `.pdf`, `.docx`, code and config files (up to `max_file_text_chars`, 3500); other files are named only |
| Forwarded messages | `(forwarded from Name)` plus the content |
| Replies | the quoted message (or the part you selected), who wrote it, and in private chat up to 2 pictures from it |
| Videos, round videos, audio files, locations, places, contacts, polls, dice, games, stories | a short text label, e.g. `[poll: Pizza tonight? (yes / no)]`, `[rolled 🎲: 4]` |
| `/start` | "(pressed Start: opened the chat with you)" |

Whether the model can see pictures or hear audio is guessed from its name; override with `enable_vision` / `enable_audio_input` (`true`/`false`). When a picture can't be shown, the bot warns once per 10 minutes (once per hour in groups): `NOT A VISION MODEL`, or `VISION IS NOT AVAILABLE: API ERROR` (then it retries once without the picture).

Several messages sent in a row (within `debounce_delay_sec`, at most `max_batch_wait_sec`) are answered together. A new message while a private reply is being written restarts the reply with everything included.

**Time awareness** (`time_awareness`, default on): the model knows the current date and time and when each message was sent (`[14:05]`, `[10-29 23:10]`), and after a long silence (`time_gap_note_hours`, 3) it is told how long it has been. Set `timezone` (e.g. `"America/New_York"` or `"-05:00"`); empty = the server clock (often UTC).

---

## 9. Live web search

* Tag `[search: query]` or the `web_search` tool. DuckDuckGo (`ddgs`) first, Bing as fallback; weather questions ("weather in Paris tomorrow") also get a live card from wttr.in. Results are cached for 10 minutes.
* At most 2 web searches and 4 tool calls per reply, to keep costs predictable.
* Settings: `enable_web_search`, `max_search_results`.

---

## 10. Logs, restarts & clean exit

* `log_level`: `DEBUG`, `INFO` (default), `WARNING`, `ERROR`. Logs go to the console and to `agent.log`.
* The bot token is never written to the log.
* **Restarts lose nothing and repeat nothing**: the position in Telegram's update stream is saved in `sessions/telegram_offset.json` after every batch. Messages that arrive while the bot is offline wait at Telegram (up to 24 hours); when the bot starts, private messages older than 3 minutes are skipped, and group messages older than 3 minutes are used only as background.
* `Ctrl+C` stops the bot cleanly; press it twice to force.
* `usage_stats` (default on): every model call adds one line of numbers (tokens, cache hits, time, purpose; never chat content) to `usage_stats/usage-<date>.jsonl`. Summarise with `python3 usage_report.py` (`--days 3`, `--price-in 0.3 --price-out 2.5 --price-cached 0.03` in USD per 1M tokens for a cost estimate).

---

## 11. MCP server (`mcp-server/telegram_mcp.py`)

An MCP server lets Claude Desktop, Cursor and other MCP clients use the companion. It reads the same `config.json`.

Tools: `tg_send_master_msg`, `tg_send_message`, `tg_send_image`, `tg_get_me`, `tg_get_chat`, `tg_delete_msg`, `tg_get_recent_messages` (from the bot's chat logs: `master`, `all`, or a session such as `group_-1001234567890`), `set_companion_status`, `web_search`, `search_chat_history`, `read_memory`, `update_memory`, `send_voice_to_master`.

Telegram lets only one program read a bot's updates, so the MCP server never polls; it reads what the running bot logs and sends through the Bot API.

```bash
python3 mcp-server/telegram_mcp.py
```
Example client entry: `{"command": "/path/to/AI2TG/venv/bin/python", "args": ["/path/to/AI2TG/mcp-server/telegram_mcp.py"]}`.

---

## 12. Configuration reference (`config.json`)

`config.json` is re-read on every reply and every ~10 seconds, so most changes need no restart (the token and proxy are read at each call too).

### Telegram & model
| Setting | Default | Meaning |
| :--- | :--- | :--- |
| `telegram_bot_token` | `""` | Token from @BotFather (required) |
| `telegram_api_base` | `https://api.telegram.org` | Bot API server; point it at your own [Bot API server](https://github.com/tdlib/telegram-bot-api) for files over 20 MB |
| `telegram_proxy` | `""` | Proxy for Telegram traffic only (`http://…`, `socks5h://…`) |
| `telegram_poll_timeout_sec` | `30` | Long-polling wait per request |
| `show_typing` | `true` | Show "typing…" / "recording voice…" while replying |
| `master_id` | `0` | Your numeric Telegram user ID: the only Master |
| `base_url` | OpenRouter | Any OpenAI-compatible chat completions endpoint (a bare base URL gets `/chat/completions` added) |
| `api_key` / `model` | | Model API key and model name |
| `max_tokens` | `1200` | Max tokens per private reply (`group_max_tokens`, 800, in groups). Thinking models count thinking too; an empty answer is retried once with 4× the budget |
| `thinking_level` | `""` | `""` (provider default), `none`, `minimal`, `low`, `medium`, `high` |
| `thinking_level_background` | `""` | For memory and glances; empty = same as `thinking_level`. `low` is cheaper |
| `thinking_api` | `auto` | How the setting is sent: OpenRouter-style `reasoning.effort`, DeepSeek `thinking`, or OpenAI `reasoning_effort` (auto-detected from `base_url`/`model`). Refused levels fall back automatically |

### Conversation
| Setting | Default | Meaning |
| :--- | :--- | :--- |
| `debounce_delay_sec` / `max_batch_wait_sec` | `2.2` / `10` | Wait for more messages before replying / the longest wait |
| `compact_threshold` / `compact_keep_recent` | `30` / `12` | AutoCompact trigger and turns kept |
| `memory_max_chars` | `8000` | Private memory size before tidying (backup first) |
| `single_message_limit_hint` | | Soft reply-length guide appended to the prompt |
| `enable_multi_bubble_reply` / `multi_bubble_delay_sec` / `private_max_bubbles` | `true` / `1.2` / `4` | Multi-bubble replies |
| `enable_autonomous_refusal` | `true` | The model may answer `[NO_REPLY]` and stay silent |
| `time_awareness` / `timezone` / `time_gap_note_hours` | `true` / `""` / `3` | See [§8](#8-what-the-bot-understands-in-a-message) |
| `usage_stats` | `true` | Token usage log, see [§10](#10-logs-restarts--clean-exit) |
| `log_level` | `INFO` | Log detail |

### Media
| Setting | Default | Meaning |
| :--- | :--- | :--- |
| `enable_vision` / `enable_audio_input` | `null` | `null` = guess from the model name; `true`/`false` to force |
| `enable_file_parser` / `max_file_text_chars` | `true` / `3500` | Read documents |
| `enable_voice_recognition` | `true` | Process voice messages |
| `asr_api_url` / `asr_api_key` / `asr_model` / `asr_language` | `""` / `""` / `whisper-1` / `en-US` | Speech-to-text |
| `enable_voice_reply` / `voice_character` | `false` / `en-US-JennyNeural` | Voice replies |
| `enable_picture_database` | `true` | Picture library |
| `enable_web_search` / `max_search_results` | `true` / `4` | Web search |

Group settings: [§15.7](#157-group-settings). Friend chat settings: [§16.3](#163-settings).

---

## 13. Linux server deployment (systemd)

```bash
git clone https://github.com/intfloatjohn/AI2TG.git /opt/AI2TG
cd /opt/AI2TG
./deploy_debian.sh          # system packages (python3, venv, ffmpeg) + venv + dependencies
nano config.json            # token, api_key, master_id
sudo cp tg-companion.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tg-companion
journalctl -u tg-companion -f
```
Edit `WorkingDirectory`/`ExecStart` in `tg-companion.service` if the folder isn't `/opt/AI2TG`.

No ports need to be opened: the bot only makes outgoing HTTPS requests (long polling).

For interactive use, `./setup.sh` once (it can fill in `config.json` and checks the token) and `./start.sh` every day.

**Moving to another computer or folder**: a copied `venv/` can't be reused (it has the old paths and Python version built in). The scripts detect that and rebuild it, so the `externally-managed-environment` error doesn't happen. Dependencies are only ever installed into `venv/`, never into the system Python.

---

## 14. Windows setup & startup

1. Install Python 3.10+ (check "Add python.exe to PATH") and, for voice, ffmpeg (`winget install Gyan.FFmpeg`).
2. Double-click **`setup_windows.bat`**: it creates `venv`, installs dependencies, prepares the TTS voice, creates `config.json` and opens it in Notepad. Fill in the token, API key and `master_id`.
3. Every day: double-click **`start.bat`** (or `start_agent.bat`). Close the window or press `Ctrl+C` to stop.

On Windows, time zone names need `pip install tzdata` (inside the venv); an offset like `"-05:00"` always works.

---

## 15. Group chat

The companion can join Telegram groups as the same character, while the Master's private memory never shows up there. It remembers what happens in groups and can recall it when the Master asks in private chat, but private chat content is never carried into a group.

### 15.1 Enabling
1. **Privacy mode**: by default a Telegram bot in a group only sees messages that @mention it, reply to it, or are commands. Name keywords, background context and glances need it to see everything: in @BotFather send `/setprivacy` → your bot → **Disable**, then **remove and re-add the bot** to each group (the setting applies when the bot joins). Making the bot a group admin also works. The log warns at startup while privacy mode is on.
2. Add the bot to the group. When someone writes there, the log shows the group's chat ID:
   ```
   Message in group "Friends" (chat ID -1001234567890) ignored: it is not in group_whitelist.
   ```
3. Add these fields to `config.json`:
   ```json
   {
     "enable_group_chat": true,
     "group_whitelist": [-1001234567890],
     "bot_name": "Hoshineko",
     "group_trigger_keywords": ["Hoshineko", "Neko"],
     "group_member_msg_limit": 10,
     "group_member_limit_window_sec": 86400
   }
   ```
No restart needed. **Only chats in `group_whitelist` are ever answered**; with an empty whitelist no group is.

If a group is upgraded to a supergroup, its chat ID changes; the log tells you the new ID to put in the whitelist.

### 15.2 When the bot replies
A group message goes to the model only if at least one of these is true:
- **Its name is mentioned**: the text contains a word from `group_trigger_keywords` (empty → `bot_name`, still empty → the bot's Telegram first name). ASCII names match whole words only, so `neko` doesn't fire on `nekomimi`.
- **The bot is @mentioned** (`@your_bot`, or `/command@your_bot`) (`group_trigger_on_at`, on by default).
- **Someone replies to one of the bot's messages** (`group_trigger_on_reply`, on by default).

Other messages don't trigger a reply; they are shown to the model as "background messages" the next time it is called. Even when called, the model may answer `[NO_REPLY]`.

**Consecutive messages**: after someone calls the bot, their next messages within `group_followup_window_sec` (10 s) belong to the same request, e.g. "@bot" and then a photo, or the rest of a photo album. If the reply is still being written, it restarts with the new message. Messages that @mention or reply to someone else don't count.

**Pictures, stickers, files and voice**:
- Pictures in the calling message, in follow-ups and in a replied-to message are opened for the model.
- From what was posted since the bot's last reply, the newest `group_context_media` (2) pictures/stickers/files/voice messages (within 5 minutes) are opened too, so "@bot what do you think?" can see a photo someone just posted.
- At most 4 pictures per reply, each with a note saying who posted it.
- Stickers the bot looked at are saved to the library automatically (with their Telegram file ID) and the model is told their ID, so it can send one back with `[PICTURE: ID]`. Stickers from the Master are shared everywhere; other members' stay in that group. Photos are not saved automatically.
- While a reply is being written, other people's new messages wait and are handled right after it.
- The reply is sent as a Telegram reply to the asker's message (`group_reply_with_quote`), optionally starting with the asker's name as a mention (`group_reply_with_at`). In forum groups it goes to the same topic.

### 15.3 Identity: user ID only
- The Master is recognised **only** by comparing the sender's numeric user ID with `master_id`.
- Every group message given to the model carries a label generated by the program: `【Master✔】` for the Master, `【Member ID:number Name:First Last (@username)】` for everyone else. `【】` typed by members, in messages or names, is replaced with `[]`, so nobody can forge `【Master✔】`.
- All permission checks happen in code, by user ID, so even a fully prompt-injected model can't reach private data or do anything it isn't allowed to. Anonymous group admins and channels posting in the group are never treated as the Master.

### 15.4 Separated memory & files
| Item | Master's private chat | Each group |
| :--- | :--- | :--- |
| Short-term context | `history.json` | `sessions/group_<chat ID>/history.json` |
| Long-term memory | `memory_summary.txt` | `sessions/group_<chat ID>/memory_summary.txt` |
| Full chat log | `chat_history.jsonl` | `sessions/group_<chat ID>/chat_history.jsonl` |
| Member message counters | — | `sessions/group_<chat ID>/quota.json` |
| Handled message IDs | — | `sessions/group_<chat ID>/seen_ids.json` |
| Pictures/voice it opened | — | `sessions/group_<chat ID>/media/` |
| Temporary downloads | `downloads/` | `downloads/group_<chat ID>/` |

- No code path reachable from a group opens the Master's private files. In a group, `[read_memory]`, `[search_history]` and `[remember]` act on that group (or the shared memory), and `agent.log` is never searched.
- **Even when the Master speaks in a group, the group-side model gets no private memory**: group replies are public and the same batch may contain other people's text.
- The Master's user ID is not hidden by default (knowing it doesn't let anyone pose as the Master). `"hide_master_id": true` replaces it with `[Master's ID hidden]` in group and friend replies unless the request came only from the Master.
- **Memory mode** (`memory_mode`):
  - `"shared"` (default): all groups and friend chats share one memory (`sessions/public/memory_summary.txt`), each entry tagged with its source (e.g. `[group "Friends" (-1001234567890)]`, `[private chat with ID:5678]`), so people are recognised across groups and private chats. Only the Master's private memory is kept apart.
  - `"separate"`: each group and each person only sees its own memory.
  - In both modes each chat's own memory file is still written, so switching later loses nothing. The model is told not to record or repeat things people clearly wouldn't want public.
- **Memory flows one way**: in private chat, "what happened in the group today?" uses `[group_recall: group ID or keyword]` / `recall_group_chat`.
- Group memory entries are tagged with their source, e.g. `(source: ID:222(Alice (@alice)))`, written by the program from real user IDs.

### 15.5 Picture library: stickers shared, photos private
One library, but every picture has a visibility scope:
- **Stickers, memes, GIFs** (including `stickers/`): public, usable everywhere.
- **Photos from the Master's private chat**: private, usable only there.
- **Pictures saved inside a group**: that group only (the Master's private chat can see them too).
- Editing or deleting pictures from a group only happens when the Master asks (checked by user ID), and only for pictures visible to that group.
- In private chat the Master can change visibility with `[PUBLIC_PICTURE: ID or tag]` / `[PRIVATE_PICTURE: ID or tag]`.

### 15.6 Messaging the Master, glances & group media memory
**Messaging the Master**: when something in a group surprises or annoys the companion, or the Master would want to know it, it can send the Master a private message (marked with the group's name).
- While replying in a group it can add `[tell_master: …]`.
- **Glance**: even when nobody calls it, it skims new group chat about every 10 minutes (only after at least 5 new messages, at most 4 times per group per hour). Usually it decides not to bother you, and it never speaks in the group while glancing. Each glance is one extra model call; `"group_glance_enabled": false` turns it off.
- At most `group_master_notify_max_per_hour` (3) such messages per hour across all groups and friend chats. Members asking it to "tell your master" are ignored. These messages are added to the private chat history, so it knows what you're replying to.

**Group media memory**: pictures and voice messages it opened are kept for `group_media_retention_days` (7) days, and the model writes a one-line description into the group log (`[MEDIA_NOTE#1: …]`, never sent). Searches and recalls then show the description and a media ID; `[review_media: media ID]` lets it look or listen again until the file is deleted (the description stays).

### 15.7 Per-member message limit
- Each member except the Master can trigger at most `group_member_msg_limit` replies per window (rolling 24 hours; if the setting is missing, 50 is used and a WARNING is logged). Only messages that call the bot count.
- After that, the member's messages are **ignored completely** (not even background) until the count drops. One WARNING is logged when someone runs out; each ignored call is logged at INFO.
- `group_member_limit_window_sec: 0` = a cap that never resets; `group_member_msg_limit: 0` = no limit. Counters live in `quota.json` and survive restarts; delete it to reset a group's counters.
- `group_member_limit_notice`: optional one-time notice when a member first hits the limit (empty = silent).

### 15.8 Group settings
| Setting | Default | Meaning |
| :--- | :--- | :--- |
| `enable_group_chat` | `false` | Master switch |
| `group_whitelist` | `[]` | Allowed chat IDs (negative numbers); empty = none |
| `bot_name` | `""` | Character name; also the default trigger word |
| `group_trigger_keywords` | `[]` | Trigger words; empty = `bot_name` or the bot's first name |
| `group_trigger_on_at` | `true` | Reply when @mentioned |
| `group_trigger_on_reply` | `true` | Reply when someone replies to the bot |
| `group_member_msg_limit` | `50` if unset (with a warning) | Replies per member per window (Master exempt; `0` = unlimited) |
| `group_member_limit_window_sec` | `86400` | Rolling window in seconds; `0` = never resets |
| `group_member_limit_notice` | `""` | Optional notice when the limit is first hit |
| `group_reply_with_quote` | `true` | Send the reply as a Telegram reply to the asker's message |
| `group_reply_with_at` | `false` | Start the reply with the asker's name as a mention |
| `group_context_messages` / `group_context_max_age_sec` | `12` / `900` | Background messages shown to the model |
| `group_followup_window_sec` | `10` | Follow-up window after calling the bot; `0` = off |
| `group_context_media` / `group_context_media_max_age_sec` | `2` / `300` | Background media opened when called |
| `group_media_retention_days` | `7` | Days opened pictures/voice are kept; `0` = forever |
| `group_master_notify_max_per_hour` | `3` | Private messages to the Master per hour (all chats); `0` = off |
| `group_glance_enabled` | `true` | Skim group chat now and then |
| `group_glance_interval_sec` / `group_glance_min_new_messages` / `group_glance_max_per_hour` | `600` / `5` / `4` | Glance timing |
| `group_max_tokens` / `group_max_bubbles` | `800` / `3` | Reply size in groups |
| `group_memory_max_chars` / `public_memory_max_chars` | `3000` / `8000` | Memory sizes before tidying |
| `memory_mode` | `"shared"` | `shared` or `separate` |
| `hide_master_id` | `false` | Hide the Master's user ID in group/friend replies |
| `group_log_ambient` | `true` | Also log non-trigger messages (for recall) |
| `group_max_file_bytes` | `8388608` | Largest group file that gets read |
| `group_debounce_delay_sec` / `group_max_batch_wait_sec` | `1.5` / `6.0` | Group batching |

### 15.9 Customising the group style
`persona/system_prompt_group.md` sets the group chat style. Edit it freely; the safety rules (identity, privacy isolation) are built into the program.

---

## 16. Friend chat

Besides the Master, the companion can chat privately with other Telegram users. Off by default: `"enable_friend_chat": true`. These chats are treated as public and untrusted, like groups.

### 16.1 Who
**Anyone can find a Telegram bot by its username**, so think about who should be able to use it (each chat costs model calls):
- `friend_whitelist`: when not empty, only these user IDs are answered. Recommended.
- `friend_blacklist`: these user IDs are never answered.
- Empty whitelist = anyone who messages the bot, except the blacklist.
- Ignored private messages are logged once per hour per person, with their user ID, so you can whitelist friends easily.

### 16.2 Rules
- **Identity by user ID only**: someone saying they are the Master changes nothing.
- **Memory**: each person has a folder `sessions/private_<user ID>/` (memory, chat log, message counter). The Master's private memory never appears there. Shared or separate memory as in [§15.4](#154-separated-memory--files).
- **Message limit**: at most `private_member_msg_limit` replies per person per window (50 if unset, with a WARNING; `0` = unlimited). `private_member_limit_notice` sets an optional one-time notice.
- **What it can do**: web search, search/remember within this chat, send public stickers. It can't modify or delete pictures or save the person's pictures into the library.
- **Telling the Master**: `[tell_master: …]` sends the Master a private note (e.g. `[private chat with Fred (ID:5678)] …`), sharing the hourly cap with groups.
- **Master recall**: "what did you talk about with Fred?" uses `[friend_recall: user ID or name]` / `recall_friend_chat` (read-only).

### 16.3 Settings
| Setting | Default | Meaning |
| :--- | :--- | :--- |
| `enable_friend_chat` | `false` | Main switch |
| `friend_whitelist` | `[]` | Only these user IDs (empty = everyone) |
| `friend_blacklist` | `[]` | User IDs never answered |
| `private_member_msg_limit` | `50` if unset (with a warning) | Replies per person per window; `0` = unlimited |
| `private_member_limit_window_sec` | `86400` | Counting window; `0` = never resets |
| `private_member_limit_notice` | `""` | One-time notice when someone hits the limit |

---

## 17. Coming from AI2QQ

This is the Telegram edition of AI2QQ. The design, file layout and behaviour are the same; what changed:

- **Transport**: the Telegram Bot API with long polling replaces NapCat/OneBot. No Docker, no QR login, no local ports.
- **Identity**: `master_qq` → `master_id` (Telegram user ID); `bot_qq` is gone (the bot's ID comes from the token); `hide_master_qq` → `hide_master_id`; labels say `ID:` instead of `QQ:`.
- **Removed (no Telegram equivalent)**: Qzone, pokes, profile likes, QQ faces (replaced by emoji faces), single-account self-chat mode, merged-forward trees (Telegram forwards arrive as separate messages and are batched).
- **New for Telegram**: `telegram_*` settings, proxy support, "typing…" indicator, real sticker/GIF resending by file ID, forum topics, `friend_whitelist` (anyone can find a bot), privacy-mode warning, update offset file.
- **English only.**

**Moving your private memory over**: the Master's files have the same format. Stop both bots and copy `history.json`, `memory_summary.txt`, `chat_history.jsonl` (and `memory_backups/`, `picture_db/` if you like) from the AI2QQ folder into this one. Group and friend sessions are tied to QQ numbers, so they don't carry over.
