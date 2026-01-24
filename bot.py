import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Read bot token from Heroku Config Vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Make sure this is set in Heroku Config Vars

# Dictionary to store temporary data per user
user_data = {}

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me the channel post link or forward the post you want to edit."
    )
    user_data[update.message.from_user.id] = {"step": "awaiting_post"}

# Message handler for links and button input
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_data:
        await update.message.reply_text("Send /start first to begin.")
        return

    step = user_data[user_id].get("step")

    # Step 1: User sends channel post link
    if step == "awaiting_post":
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text(
            "Got it! Now send me your button format.\n\n"
            "Format example:\n"
            "Button text 1 - http://www.example.com/ | Button text 2 - http://www.example2.com/ | Button text 3 - http://www.example3.com/"
        )
        return

    # Step 2: User sends button format
    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]

        # Parse buttons
        buttons_raw = [b.strip() for b in text.split("|")]
        keyboard = []
        for btn in buttons_raw:
            if "-" in btn:
                label, url = btn.split("-", 1)
                keyboard.append([InlineKeyboardButton(label.strip(), url=url.strip())])

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # Extract chat_id and message_id from t.me/c/<channel_id>/<message_id>
            if "t.me/c/" in post_link:
                parts = post_link.split("/")
                chat_id = int("-100" + parts[-2])
                message_id = int(parts[-1])
            else:
                await update.message.reply_text("Invalid channel post link format!")
                return

            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            await update.message.reply_text("✅ Buttons added successfully!")

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

        # Reset user step
        user_data[user_id] = {"step": "awaiting_post"}

# Main function
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set! Make sure you set BOT_TOKEN Config Var on Heroku.")

    # v20+ ApplicationBuilder
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    app.run_polling()

# Entry point
if __name__ == "__main__":
    main()
