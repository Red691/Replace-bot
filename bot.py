import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Read bot token from Heroku Config Vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set this in Heroku Config Vars

# Temporary user data
user_data = {}

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me the channel post link or forward the post you want to edit."
    )
    user_data[update.message.from_user.id] = {"step": "awaiting_post"}

# Parser: Enter = vertical, double space = horizontal
def parse_buttons_by_lines(text: str):
    keyboard = []

    lines = text.split("\n")  # Each line = new row (vertical)
    for line in lines:
        line = line.strip()
        if not line:
            continue

        row_buttons = []
        # Split by double space for horizontal buttons
        for btn_text in line.split("  "):  
            btn_text = btn_text.strip()
            if "-" in btn_text:
                label, url = btn_text.split("-", 1)
                label, url = label.strip(), url.strip()
                if label and url:
                    row_buttons.append(InlineKeyboardButton(label, url=url))
        if row_buttons:
            keyboard.append(row_buttons)

    return keyboard

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_data:
        await update.message.reply_text("Send /start first to begin.")
        return

    step = user_data[user_id].get("step")

    # Step 1: Get post link
    if step == "awaiting_post":
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text(
            "Got it! Now send me your button format.\n\n"
            "Rules:\n"
            "- Each line = new row (vertical buttons)\n"
            "- Double space in line = multiple buttons in same row (horizontal)\n"
            "- Format: Button Text - URL\n\n"
            "Example:\n"
            "🖥 Watch & Download 📥 - https://t.me/example1\n"
            "🌐 Main channel - https://t.me/example2  ⛩Anime List - https://t.me/example3\n"
            "📮 Request Your Anime Here 📮 - https://t.me/example4"
        )
        return

    # Step 2: Parse button format
    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]

        keyboard = parse_buttons_by_lines(text)
        if not keyboard:
            await update.message.reply_text(
                "❌ No valid buttons found! Use the correct format."
            )
            return

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # Extract chat_id and message_id from private channel link
            if "t.me/c/" in post_link:
                parts = post_link.split("/")
                chat_id = int("-100" + parts[-2])
                message_id = int(parts[-1])
            else:
                await update.message.reply_text("Invalid channel post link format!")
                return

            # Edit message buttons
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            await update.message.reply_text("✅ Buttons added/updated successfully!")

        except Exception as e:
            error_msg = str(e)
            if "Message_id_invalid" in error_msg:
                await update.message.reply_text(
                    "❌ Cannot edit this message. Make sure the bot posted it."
                )
            else:
                await update.message.reply_text(f"❌ Error: {error_msg}")

        # Reset user step
        user_data[user_id] = {"step": "awaiting_post"}

# Main function
def main():
    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN is not set! Make sure you set BOT_TOKEN Config Var on Heroku."
        )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
