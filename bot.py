import re
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MAX_BUTTONS_PER_ROW = int(os.environ.get("MAX_BUTTONS_PER_ROW", 4))

def parse_buttons(button_text):
    pattern = r"\[\((.*?)\)-/replace (.*?)\]"
    match = re.search(pattern, button_text)
    if not match:
        return None, None

    buttons_raw, post_link = match.groups()
    buttons_list = []

    for b in buttons_raw.split('|'):
        text, url = b.strip().split(' - ')
        buttons_list.append(InlineKeyboardButton(text, url=url.strip()))

    # Split buttons into multiple rows
    rows = [buttons_list[i:i+MAX_BUTTONS_PER_ROW] for i in range(0, len(buttons_list), MAX_BUTTONS_PER_ROW)]
    return rows, post_link.strip()

async def replace_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format: /replace [(Button1 - URL1 | Button2 - URL2)-/replace post_link]")
        return

    input_text = " ".join(context.args)
    button_rows, post_link = parse_buttons(input_text)
    if not button_rows:
        await update.message.reply_text("Invalid format!")
        return

    reply_markup = InlineKeyboardMarkup(button_rows)

    try:
        parts = post_link.rstrip('/').split('/')
        chat_id = "@" + parts[-2]
        message_id = int(parts[-1])

        await context.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup
        )
        await update.message.reply_text("✅ Buttons updated successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("replace", replace_buttons))
app.run_polling()
