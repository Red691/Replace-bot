# btn_replace_plugin.py
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from telegram.error import RetryAfter

# user_data for temporary storage
user_data = {}

def register_plugin(app):
    app.add_handler(CommandHandler("btn_rep_link", btn_rep_link))
    app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

# Regex to parse Telegram links
LINK_RE = re.compile(r"https://t.me/c/(\d+)/(\d+)")

def extract_ids(link: str):
    m = LINK_RE.match(link.strip())
    if not m:
        return None, None
    chat_id = int("-100" + m.group(1))
    message_id = int(m.group(2))
    return chat_id, message_id

# Command
async def btn_rep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {"step": "awaiting_links"}
    await update.message.reply_text(
        "Send command in format:\n"
        "/btn_rep_link <start_link> - <end_link> | <button_text> | <new_bot_username>"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        return
    step = user_data[user_id].get("step")

    if step == "awaiting_links":
        text = update.message.text
        try:
            link_part, btn_text, new_bot = map(str.strip, text.split("|"))
            start_link, end_link = map(str.strip, link_part.split("-", 1))
        except:
            await update.message.reply_text("❌ Invalid format. Use:\nlink1 - link2 | button_text | new_bot_username")
            return

        start_chat, start_msg = extract_ids(start_link)
        end_chat, end_msg = extract_ids(end_link)

        if start_chat != end_chat:
            await update.message.reply_text("❌ Links must be from the same chat")
            return

        msg_ids = list(range(start_msg, end_msg + 1))
        edited, skipped, errors = 0, 0, []

        for mid in msg_ids:
            try:
                msg = await context.bot.get_message(start_chat, mid)
                if not msg.reply_markup:
                    skipped += 1
                    continue

                buttons = msg.reply_markup.inline_keyboard
                changed = False
                for row in buttons:
                    for btn in row:
                        if btn_text.lower() in btn.text.lower() and "t.me/" in btn.url:
                            parts = btn.url.split("?start=")
                            payload = parts[1] if len(parts) > 1 else ""
                            btn.url = f"https://t.me/{new_bot}?start={payload}"
                            changed = True

                if changed:
                    await context.bot.edit_message_reply_markup(
                        chat_id=start_chat,
                        message_id=mid,
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                    edited += 1
                    await asyncio.sleep(2)
                else:
                    skipped += 1
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
                continue
            except Exception as e:
                errors.append(f"Msg {mid}: {e}")

        await update.message.reply_text(
            f"✅ Done!\nEdited: {edited}\nSkipped: {skipped}\nErrors: {len(errors)}"
        )
        user_data[user_id] = {}
