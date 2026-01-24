from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, filters
# Your bot token
BOT_TOKEN = os.environ.get("YOUR_BOT_TOKEN")

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
            # Extract chat_id and message_id from post link
            # Telegram private channel links look like t.me/c/<channel_id>/<message_id>
            if "t.me/c/" in post_link:
                parts = post_link.split("/")
                chat_id = int("-100" + parts[-2])  # Channel ID format for private channels
                message_id = int(parts[-1])
            else:
                update.message.reply_text("Invalid channel post link format!")
                return

            # Edit the channel post with buttons
            context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            update.message.reply_text("✅ Buttons added successfully!")

        except Exception as e:
            update.message.reply_text(f"❌ Error: {e}")

        # Reset user step
        user_data[user_id] = {"step": "awaiting_post"}

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
