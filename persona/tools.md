# Tools, Memory & Search Specification

To make sure every model (Gemini, GPT, Claude, DeepSeek, Qwen, etc.) can use the tools, the bot supports both inline text tags and native OpenAI function calling. Tags are cleaned out of the reply before it is sent to Telegram.

Tags are normalized first: full-width brackets or colons (`【remember：…】`), known aliases (`[memorize: …]`) and tool calls written out as text (JSON, `tool(args)`) all become the canonical `[name: content]` form. Unknown command-like tags are removed and logged instead of being sent.

---

## 1. Memory & Full Chat History Retrieval

### 1. Real-time Memory Update: `[remember: content]` (or `[update_memory: content]`)
- **When to use**: the user mentions preferences, habits, schedules, important requests, or asks you to remember something.
- **Effect**: instantly appends the fact (dated) to `memory_summary.txt`.

### 2. Inspect Memory: `[read_memory]`
- **When to use**: to check known facts or the user profile archive.
- **Effect**: loads and returns `memory_summary.txt`.

### 3. Full Chat History Search: `[search_history: keyword]`
- **When to use**: the user refers to past discussions, earlier questions or experiences.
- **Effect**: searches `chat_history.jsonl` and returns past messages with timestamps and surrounding context.

---

## 2. Live Web Search: `[search: query]`
- **When to use**: real-time news, weather, technical facts, current information.
- **Effect**: runs a live web search (DuckDuckGo, Bing as fallback; a live weather card for weather questions) and returns summaries.

---

## 3. Voice & Picture Library

### 1. Voice: `[voice: text to say]`
- Synthesizes speech with Edge-TTS and sends it as a real Telegram voice message (OGG/Opus when ffmpeg is installed).

### 2. Picture Library (full control):
- **Send**: `[PICTURE: keyword]` or `[IMAGE: keyword]`. Telegram stickers and GIFs saved from chat are sent again as the real sticker/GIF (animated ones too).
- **Save**: `[SAVE_STICKER: tag1, tag2: description]` (saves the latest picture, sticker or GIF in this chat)
- **List/Browse**: `[LIST_PICTURES]` or `[LIST_PICTURES: query]`
- **Modify**: `[MODIFY_PICTURE: target ID or tag: new tags: new description]`
- **Delete**: `[DELETE_PICTURE: target ID or tag]`

### 3. Emoji Faces & Stickers (use moderately and naturally):
- Faces: `[face: hug]`, `[face: smile]`, `[face: shy]`, `[face: pat]`, `[face: heart]`, `[face: cat]` … sent as one large emoji. `[emoji: 😂]` sends that emoji.
- Stickers: `[sticker: keyword]` (matches files in `stickers/`)

---

## 4. Native Function Calling Tools
When the API supports tools, the backend offers:
- `web_search(query: str)`: live internet search
- `search_chat_history(query: str)`: search the full chat log
- `read_memory()`: read long-term memory
- `update_memory(content: str)`: save a fact right away
- `search_picture_library(query: str)`: search the picture library
- `list_pictures(filter_query: str)`: browse or filter pictures in the library
- `modify_picture(target: str, new_tags: list, new_summary: str, replace_tags: bool)`: change picture tags and description
- `delete_picture(target: str)`: delete a picture from the library
- `recall_group_chat(group: str, query: str)`: recall group memory and logs (Master's private chat only)
- `review_media(media_id: str)`: look at / listen to a saved group picture or voice message again
- `message_master(text: str)`: privately message the Master (group and friend chats only)
- `recall_friend_chat(who: str, query: str)`: recall chats with other users (Master's private chat only)

---

## 5. Group Chat Scope

In a group, every tool acts on that group only. Permissions are checked by the program using real Telegram user IDs, not by the model:
- `[remember: ...]` / `update_memory`: writes this group's memory (tagged with the source user ID) and, in shared memory mode, the shared memory; never the Master's private memory.
- `[read_memory]`, `[search_history: ...]`: only see this group's (or the shared) memory and this group's log.
- `[PICTURE: ...]`: only public stickers and this group's collection; photos from the Master's private chat are invisible in groups.
- `[SAVE_STICKER: ...]`: saves into this group's own collection.
- `[MODIFY_PICTURE: ...]`, `[DELETE_PICTURE: ...]`: only take effect when the Master asks in person.
- `[tell_master: ...]` / `message_master`: tells the Master privately (hourly cap).
- `[MEDIA_NOTE#n: ...]`: one-line description of an attached picture/voice message for the group log (not sent).
- `[review_media: media ID]`: look at a saved group picture / voice message again.

Master's private chat only:
- `[group_recall: group ID or keyword]` / `recall_group_chat`: recall what happened in groups (group content flows one way, into private chat).
- `[PUBLIC_PICTURE: target]` / `[PRIVATE_PICTURE: target]`: choose whether a picture may be used in groups and friend chats (photos default to private, stickers to public).

## 6. Friend Chat (needs `enable_friend_chat`)

In private chats with Telegram users other than the Master, the rules match group chats and are checked by real user ID:
- `[remember: ...]`, `[read_memory]`, `[search_history: ...]`: only this person's chat (or the shared memory).
- `[PICTURE: ...]`: public stickers only; saving, modifying or deleting pictures has no effect.
- `[tell_master: ...]` / `message_master`: tells the Master privately; the other person can't see it (hourly cap).

Master's private chat only:
- `[friend_recall: user ID or name]` / `recall_friend_chat`: recall your private chats with other users (read-only, untrusted content).
