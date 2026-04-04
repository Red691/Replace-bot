import asyncio
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

EDIT_DELAY = 2  # seconds
LINK_RE = re.compile(r"https://t\.me/c/(\d+)/(\d+)")

def extract_ids(link: str):
    m = LINK_RE.match(link.strip())
    if not m:
        return None, None
    chat_id = int("-100" + m.group(1))
    msg_id = int(m.group(2))
    return chat_id, msg_id

def update_button_url(url: str, new_bot: str):
    if not url or not url.startswith("https://t.me/"):
        return url
    match = re.match(r"https://t\.me/([^?]+)\?start=(.+)", url)
    if not match:
        return url
    payload = match.group(2)
    return f"https://t.me/{new_bot}?start={payload}"

async def btn_replace_cmd(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    try:
        text = update.message.text[len("/btn_rep_link "):].strip()
        link_part, btn_text, new_bot = map(str.strip, text.split("|"))
        start_link, end_link = map(str.strip, link_part.split("-", 1))
    except Exception:
        await update.message.reply_text("❌ Invalid format.\nUse:\n/start_link - end_link | button_text | new_bot")
        return

    start_chat, start_msg = extract_ids(start_link)
    end_chat, end_msg = extract_ids(end_link)
    if None in (start_chat, start_msg, end_chat, end_msg) or start_chat != end_chat:
        await update.message.reply_text("❌ Invalid links or messages must be from same chat.")
        return

    chat_id = start_chat
    msg_ids = range(start_msg, end_msg + 1)
    edited, skipped, errors = 0, 0, []

    await update.message.reply_text(f"⚡ Processing {len(msg_ids)} messages...")

    for mid in msg_ids:
        try:
            msg = await context.bot.get_message(chat_id, mid)
            if not msg or not msg.reply_markup:
                skipped += 1
                continue

            markup: InlineKeyboardMarkup = msg.reply_markup
            new_rows, changed = [], False
            for row in markup.inline_keyboard:
                new_row = []
                for btn in row:
                    if btn_text.lower() in (btn.text or "").lower():
                        new_url = update_button_url(btn.url, new_bot)
                        if new_url != btn.url:
                            btn = InlineKeyboardButton(btn.text, url=new_url)
                            changed = True
                    new_row.append(btn)
                new_rows.append(new_row)

            if changed:
                await context.bot.edit_message_reply_markup(chat_id, mid, InlineKeyboardMarkup(new_rows))
                edited += 1
                print(f"✅ Edited {mid}")
            else:
                skipped += 1

            await asyncio.sleep(EDIT_DELAY)
        except Exception as e:
            errors.append(f"Msg {mid}: {e}")

    result = f"✅ Done! Edited: {edited}, Skipped: {skipped}"
    if errors:
        result += "\nErrors:\n" + "\n".join(errors)
    await update.message.reply_text(result)


def register_plugin(app):
    app.add_handler(CommandHandler("btn_rep_link", btn_replace_cmd))
