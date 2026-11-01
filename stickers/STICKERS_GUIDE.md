# Stickers Folder Guide

This folder holds your own stickers, memes and photos that the companion can send on its own.

---

## 1. Adding a sticker
1. Put a `.jpg`, `.png`, `.gif` or `.webp` file in this folder.
2. Give it a short, memorable file name. The name is what the bot matches on:
   - `heart.jpg` (heart / love)
   - `wave.jpg` (hello / goodbye)
   - `sleep.jpg` (good night)
   - `pout.jpg` (sulking / annoyed)
   - `avatar.jpg` (selfie)

No restart is needed: the folder is read every time a sticker is sent.

How each file type arrives in Telegram:
- `.webp`: sent as a Telegram sticker (falls back to a photo if Telegram refuses it).
- `.gif`: sent as a GIF (Telegram "animation").
- `.jpg` / `.png`: sent as a photo.

---

## 2. How the bot finds and sends it
When the model writes `[sticker: keyword]` in a reply, the bot:
1. Looks for a file whose name contains the keyword (or the other way round), ignoring case.
2. If none matches, tries built-in aliases (for example "love" also finds `heart`).
3. If there is still no match, searches the picture library (`[PICTURE: keyword]`).
4. Sends the image to the chat. The tag itself is removed from the text.

Stickers in this folder are also added to the picture library automatically, so `[PICTURE: keyword]` and the `search_picture_library` tool can find them too. In group chats they count as public pictures.

Telegram stickers people send to the bot can be saved too (`[SAVE_STICKER: …]`, or automatically in the Master's private chat). Those are remembered with their Telegram file ID and sent back as the real sticker, animated ones included.

---

## 3. Letting the model know about new stickers
List your stickers in the persona prompt so the model knows they exist. In `persona/system_prompt.md`, extend the line that starts with "Custom stickers", for example:

```
- Custom stickers: `[sticker: heart]`, `[sticker: wave]`, `[sticker: sleep]`, `[sticker: your-new-sticker]`
```

The model will then pick a fitting sticker when it wants to.
