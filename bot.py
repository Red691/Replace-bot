import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
from config import BOT_TOKEN, CHANNEL_ID
# Dictionary to store temporary data per user
user_data = {}

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hello! Send me the channel post link or forward the post you want to edit."
    )
    user_data[update.message.from_user.id] = {"step": "awaiting_post"}

def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_data:
        update.message.reply_text("Send /start first to begin.")
        return

    step = user_data[user_id].get("step")

    # Step 1: User sends channel post link
    if step == "awaiting_post":
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_buttons"
        update.message.reply_text(
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
            if "t.me/c/" in post_link:
                parts = post_link.split("/")
                chat_id = int("-100" + parts[-2])
                message_id = int(parts[-1])
            else:
                update.message.reply_text("Invalid channel post link format!")
                return

            context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            update.message.reply_text("✅ Buttons added successfully!")

        except Exception as e:
            update.message.reply_text(f"❌ Error: {e}")

        user_data[user_id] = {"step": "awaiting_post"}

def main():
    BOT_TOKEN = os.environ.get("TOKEN")  # Heroku Config Var key

    # v20+ ApplicationBuilder
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
