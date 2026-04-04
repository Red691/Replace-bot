# btn_replace_plugin.py
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import RetryAfter

# Temporary user storage
user_data = {}

# Regex to extract chat_id & message_id from Telegram links
LINK_RE = re.compile(r"https://t\.me/c/(\d+)/(\d+)")

# Helper: extract chat_id and message_id
def extract_ids(link: str):
    m = LINK_RE.match(link.strip())
    if not m:
        return None, None
    chat_id = int("-100" + m.group(1))
    message_id = int(m.group(2))
    return chat_id, message_id

# Helper: replace only bot username in URL
def replace_bot_in_url(url: str, new_bot: str):
    if not url.startswith("https://t.me/"):
        return url
    parts = url.split("?start=")
    payload = parts[1] if len(parts) > 1 else ""
    return f"https://t.me/{new_bot}?start={payload}"

# /btn_rep_link command
async def btn_rep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"step": "awaiting_links"}
    await update.message.reply_text(
        "Send in format:\n"
        "/btn_rep_link <start_link> - <end_link> | <button_text> | <new_bot_username>"
    )

# Message handler to process the command
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or user_data[user_id].get("step") != "awaiting_links":
        return

    text = update.message.text
    try:
        links_part, btn_text, new_bot = map(str.strip, text.split("|"))
        start_link, end_link = map(str.strip, links_part.split("-", 1))
    except:
        await update.message.reply_text(
            "❌ Invalid format. Use:\nlink1 - link2 | button_text | new_bot_username"
        )
        return

    start_chat, start_id = extract_ids(start_link)
    end_chat, end_id = extract_ids(end_link)

    if start_chat != end_chat:
        await update.message.reply_text("❌ Start and End links must be from the same chat.")
        return

    edited, skipped, errors = 0, 0, []
    for msg_id in range(start_id, end_id + 1):
        try:
            msg = await context.bot.get_chat(start_chat).get_message(msg_id)
            if not msg.reply_markup:
                skipped += 1
                continue

            new_rows = []
            changed = False
            for row in msg.reply_markup.inline_keyboard:
                new_row = []
                for btn in row:
                    if btn_text.lower() in btn.text.lower() and "t.me/" in btn.url:
                        new_row.append(
                            InlineKeyboardButton(btn.text, url=replace_bot_in_url(btn.url, new_bot))
                        )
                        changed = True
                    else:
                        new_row.append(btn)
                new_rows.append(new_row)

            if changed:
                await context.bot.edit_message_reply_markup(
                    chat_id=start_chat,
                    message_id=msg_id,
                    reply_markup=InlineKeyboardMarkup(new_rows)
                )
                edited += 1
                await asyncio.sleep(2)
            else:
                skipped += 1

        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            continue
        except Exception as e:
            errors.append(f"Msg {msg_id}: {e}")

    await update.message.reply_text(
        f"✅ Done!\nEdited: {edited}\nSkipped: {skipped}\nErrors: {len(errors)}"
    )
    user_data[user_id] = {}
