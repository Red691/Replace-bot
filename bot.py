import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Read bot token from Heroku Config Vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set this in Heroku Config Vars

# Dictionary to store temporary data per user
user_data = {}

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me the channel post link or forward the post you want to edit."
    )
    user_data[update.message.from_user.id] = {"step": "awaiting_post"}

# Helper function to parse buttons dynamically
def parse_buttons(text: str):
    keyboard = []

    # Split by '|' first (landscape/vertical)
    for group in text.split("|"):
        group = group.strip()
        if not group:
            continue

        # Split by space for horizontal buttons
        buttons_in_group = []
        for btn in group.split("  "):  # double space separates horizontal buttons
            btn = btn.strip()
            if "-" in btn:
                label, url = btn.split("-", 1)
                label, url = label.strip(), url.strip()
                if label and url:
                    buttons_in_group.append(InlineKeyboardButton(label, url=url))

        if buttons_in_group:
            keyboard.append(buttons_in_group)

    return keyboard

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
            "Horizontal buttons (same row): Button1 - URL1  Button2 - URL2\n"
            "Vertical buttons (new row): Button1 - URL1 | Button2 - URL2 | Button3 - URL3\n"
            "You can mix both!"
        )
        return

    # Step 2: User sends button format
    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]

        # Parse buttons
        keyboard = parse_buttons(text)
        if not keyboard:
            await update.message.reply_text(
                "❌ No valid buttons found! Use the correct format."
            )
            return

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

            # Replace old buttons with new ones
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
