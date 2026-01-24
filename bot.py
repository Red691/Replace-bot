import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ---------- Button Parser ----------
def parse_buttons(text):
    buttons = []
    lines = text.strip().split("\n")
    for line in lines:
        if "-" in line:
            btn_text, url = line.split("-", 1)
            buttons.append(InlineKeyboardButton(btn_text.strip(), url=url.strip()))
    return buttons

# ---------- /new Command ----------
async def new_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Must be used in channel
    if message.chat.type != "channel":
        await message.reply_text("❌ Ye command sirf channel me use karo.")
        return

    # Must reply to a post
    if not message.reply_to_message:
        await message.reply_text("❌ Kisi channel post ko reply karke /new bhejo.")
        return

    # Must contain button data
    if not context.args:
        await message.reply_text("❌ Format:\nButton text - URL")
        return

    # Parse new buttons
    text_input = " ".join(context.args)
    new_buttons = parse_buttons(text_input)

    # Get old buttons if exist
    old_markup = message.reply_to_message.reply_markup
    old_buttons = []
    if old_markup:
        for row in old_markup.inline_keyboard:
            old_buttons.extend(row)

    # Combine old + new
    all_buttons = old_buttons + new_buttons

    # Build markup (2 buttons per row)
    rows = [all_buttons[i:i+2] for i in range(0, len(all_buttons), 2)]
    markup = InlineKeyboardMarkup(rows)

    # Edit original channel post
    await context.bot.edit_message_reply_markup(
        chat_id=message.chat_id,
        message_id=message.reply_to_message.message_id,
        reply_markup=markup
    )

    # Confirmation
    await message.reply_text("✅ Buttons added successfully!")

# ---------- Run ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("new", new_buttons))
app.run_polling()
