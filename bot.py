from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

BOT_TOKEN = "YOUR_BOT_TOKEN"
PRIVATE_CHANNEL_ID = "@your_channel_username_or_id"
# Function to parse buttons from your format
def parse_buttons(text):
    buttons = []
    lines = text.strip().split("\n")
    for line in lines:
        if "-" in line:
            btn_text, url = line.split("-", 1)
            buttons.append(InlineKeyboardButton(btn_text.strip(), url=url.strip()))
    return InlineKeyboardMarkup.from_row(buttons)  # all in single row

# Command to add new buttons to an existing message
async def add_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Use this bot in private chat only!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a channel message to add buttons!")
        return

    if not context.args:
        await update.message.reply_text("Send buttons in format:\nButton text - URL")
        return

    new_buttons_markup = parse_buttons(" ".join(context.args))

    # Get existing buttons
    old_markup = update.message.reply_to_message.reply_markup
    if old_markup:
        existing_buttons = [btn for row in old_markup.inline_keyboard for btn in row]
    else:
        existing_buttons = []

    # Combine old + new buttons
    combined_buttons = existing_buttons + [btn for row in new_buttons_markup.inline_keyboard for btn in row]

    # Update message
    combined_markup = InlineKeyboardMarkup.from_row(combined_buttons)

    try:
        await context.bot.edit_message_reply_markup(
            chat_id=update.message.reply_to_message.chat_id,
            message_id=update.message.reply_to_message.message_id,
            reply_markup=combined_markup
        )
        await update.message.reply_text("✅ New buttons added successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

# Command to post a new message with buttons
async def post_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Send buttons in format:\nButton text - URL")
        return

    button_text = " ".join(context.args)
    markup = parse_buttons(button_text)

    await context.bot.send_message(
        chat_id=PRIVATE_CHANNEL_ID,
        text="Here is a post with buttons:",
        reply_markup=markup
    )
    await update.message.reply_text("✅ Message posted to channel!")

# Run the bot
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("new", add_buttons))
app.add_handler(CommandHandler("post", post_buttons))

app.run_polling()
