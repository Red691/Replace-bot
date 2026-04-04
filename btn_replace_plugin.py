# btn_replace_plugin.py
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import RetryAfter

# Temporary user data
user_data = {}

# Regex to parse Telegram post links
LINK_RE = re.compile(r"https://t\.me/c/(\d+)/(\d+)")

def extract_ids(link: str):
    """Extract chat_id and message_id from t.me/c/ link"""
    m = LINK_RE.match(link.strip())
    if not m:
        return None, None
    chat_id = int("-100" + m.group(1))
    message_id = int(m.group(2))
    return chat_id, message_id

def replace_bot_in_url(url, new_bot):
    """Replace the bot username in a t.me URL preserving payload"""
    if not url.startswith("https://t.me/"):
        return url
    parts = url.split("?start=")
    payload = parts[1] if len(parts) > 1 else ""
    return f"https://t.me/{new_bot}?start={payload}"

async def btn_rep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to start bot replacement"""
    user_data[update.effective_user.id] = {"step": "awaiting_links"}
    await update.message.reply_text(
        "Send in format:\n"
        "<start_link> - <end_link> | <button_text_partial> | <new_bot_username>\n\n"
        "Partial match will work, emojis and extra spaces ignored."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle message input after /btn_rep_link"""
    user_id = update.effective_user.id
    if user_id not in user_data:
        return
    if user_data[user_id].get("step") != "awaiting_links":
        return

    text = update.message.text
    try:
        link_part, btn_text, new_bot = map(str.strip, text.split("|"))
        start_link, end_link = map(str.strip, link_part.split("-", 1))
    except:
        await update.message.reply_text(
            "❌ Invalid format.\nUse: link1 - link2 | button_text_partial | new_bot_username"
        )
        return

    start_chat, start_msg = extract_ids(start_link)
    _, end_msg = extract_ids(end_link)

    if not start_chat or not start_msg or not end_msg:
        await update.message.reply_text("❌ Invalid links.")
        return

    msg_ids = list(range(start_msg, end_msg + 1))
    edited, skipped, errors = 0, 0, []

    for mid in msg_ids:
        try:
            msg = await context.bot.get_chat(start_chat).get_message(mid)
            if not msg.reply_markup or not msg.reply_markup.inline_keyboard:
                skipped += 1
                continue

            buttons = msg.reply_markup.inline_keyboard
            changed = False
            new_rows = []

            for row in buttons:
                new_row = []
                for btn in row:
                    # Normalize text for partial match ignoring emojis/spaces
                    normalized_btn = "".join(c for c in btn.text if c.isalnum()).lower()
                    normalized_input = "".join(c for c in btn_text if c.isalnum()).lower()

                    if normalized_input in normalized_btn and "t.me/" in btn.url:
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
                    message_id=mid,
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
            errors.append(f"Msg {mid}: {e}")

    await update.message.reply_text(
        f"✅ Done!\nEdited: {edited}\nSkipped: {skipped}\nErrors: {len(errors)}"
    )
    user_data[user_id] = {}
