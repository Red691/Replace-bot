import re
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, Update
from telegram.error import RetryAfter

LINK_RE = r"https://t\.me/c/(\d+)/(\d+)"

def replace_bot_in_url(url, new_bot):
    if not url.startswith("https://t.me/"):
        return url
    parts = url.split("?start=")
    if len(parts) != 2:
        return url
    payload = parts[1]
    return f"https://t.me/{new_bot}?start={payload}"

def extract_chat_and_msg(link):
    m = re.match(LINK_RE, link)
    if not m:
        return None, None
    chat_id = int("-100" + m.group(1))
    msg_id = int(m.group(2))
    return chat_id, msg_id

async def btn_rep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    try:
        text = update.message.text[len("/btn_rep_link "):].strip()
        links_part, button_text, new_bot = map(str.strip, text.split("|", 2))
        start_link, end_link = map(str.strip, links_part.split("-", 1))
        chat_id, start_id = extract_chat_and_msg(start_link)
        _, end_id = extract_chat_and_msg(end_link)

        await update.message.reply_text(f"✅ Editing messages {start_id}-{end_id}...")

        for msg_id in range(start_id, end_id + 1):
            try:
                msg = await context.bot.get_chat(chat_id).get_message(msg_id)
                if not msg.reply_markup:
                    print(f"Skipped {msg_id} (no buttons)")
                    continue
                new_rows = []
                edited = False
                for row in msg.reply_markup.inline_keyboard:
                    new_row = []
                    for btn in row:
                        if button_text.lower() in btn.text.lower():
                            new_row.append(InlineKeyboardButton(btn.text, url=replace_bot_in_url(btn.url, new_bot)))
                            edited = True
                        else:
                            new_row.append(btn)
                    new_rows.append(new_row)
                if edited:
                    await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(new_rows))
                    print(f"Edited {msg_id}")
                else:
                    print(f"Skipped {msg_id} (no matching button)")
                await asyncio.sleep(2)
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except Exception as e:
                print(f"Error {msg_id}: {e}")
        await update.message.reply_text("✅ Done!")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")
