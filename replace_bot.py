from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import re

BOT_TOKEN = "YOUR_BOT_TOKEN"


# --- extract chat_id and message_id from t.me link ---
def extract_ids(link):
    # public channel
    m = re.match(r"https://t.me/([^/]+)/(\d+)", link)
    if m:
        username = m.group(1)
        msg_id = int(m.group(2))
        return username, msg_id

    # private channel (t.me/c/)
    m = re.match(r"https://t.me/c/(\d+)/(\d+)", link)
    if m:
        chat_id = int("-100" + m.group(1))
        msg_id = int(m.group(2))
        return chat_id, msg_id

    return None, None


# --- replace text ---
async def rtext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage:\n/rtext <post_link> <new_text>")
        return

    link = context.args[0]
    new_text = " ".join(context.args[1:])
    chat_id, msg_id = extract_ids(link)

    if not chat_id:
        await update.message.reply_text("Invalid Telegram post link")
        return

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=new_text
        )
        await update.message.reply_text("✅ Text replaced")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# --- replace caption ---
async def rcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = context.args[0]
    new_caption = " ".join(context.args[1:])
    chat_id, msg_id = extract_ids(link)

    try:
        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=msg_id,
            caption=new_caption
        )
        await update.message.reply_text("✅ Caption replaced")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# --- replace button ---
async def rbtn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = context.args[0]
    data = " ".join(context.args[1:])
    old, new, url = data.split("|")

    chat_id, msg_id = extract_ids(link)

    msg = await context.bot.get_chat(chat_id)
    message = await context.bot.forward_message(update.effective_chat.id, chat_id, msg_id)

    # get original markup
    orig = message.reply_markup
    if not orig:
        await update.message.reply_text("No buttons in original message")
        return

    new_kb = []
    for row in orig.inline_keyboard:
        new_row = []
        for btn in row:
            if btn.text == old:
                new_row.append(InlineKeyboardButton(new, url=url))
            else:
                new_row.append(btn)
        new_kb.append(new_row)

    await context.bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=msg_id,
        reply_markup=InlineKeyboardMarkup(new_kb)
    )

    await update.message.reply_text("✅ Button replaced")


# --- start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Channel Replace Bot Ready ✅\n\n"
        "Commands in PM:\n"
        "/rtext <post_link> <new_text>\n"
        "/rcap <post_link> <new_caption>\n"
        "/rbtn <post_link> old|new|url\n\n"
        "Make bot admin with Edit permission in channel."
    )


app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("rtext", rtext))
app.add_handler(CommandHandler("rcap", rcap))
app.add_handler(CommandHandler("rbtn", rbtn))

print("Bot running...")
app.run_polling()
