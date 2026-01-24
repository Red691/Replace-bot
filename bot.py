from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import re
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ===== CONFIG =====

# Private channel username (without @)
CHANNEL_USERNAME = "YourPrivateChannel"

# Replace Button URLs
BTN1 = "https://t.me/Hanime_hentai69_bot?start=BQADAQAD5ggAAkeKiUXzmHA-_Ip-6hYE"
BTN2 = "https://t.me/Hanime_hentai69_bot?start=BQADAQAD7QgAAkeKiUXCgQE095X8WxYE"
BTN3 = "https://t.me/Hanime_hentai69_bot?start=BQADAQAD-ggAAkeKiUWYqvqRl7PwUxYE"
# ===================


def extract_post_id(link: str):
    match = re.search(r"/(\d+)$", link)
    return int(match.group(1)) if match else None


def default_keyboard():
    keyboard = [
        [InlineKeyboardButton("Button 1", url=BTN1)],
        [InlineKeyboardButton("Button 2", url=BTN2)],
        [InlineKeyboardButton("Button 3", url=BTN3)]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Replace Bot Online\n\n"
        "Commands:\n"
        "/replace_text <channel_post_link>\n"
        "/replace_media <channel_post_link>\n"
        "/replace_buttons <channel_post_link>\n\n"
        "Use command by replying to a message."
    )


# --- Replace Text ---
async def replace_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a text message.")

    if not context.args:
        return await update.message.reply_text("Use: /replace_text <channel_post_link>")

    post_id = extract_post_id(context.args[0])
    if not post_id:
        return await update.message.reply_text("Invalid channel post link.")

    msg = update.message.reply_to_message
    new_text = msg.text or msg.caption

    if not new_text:
        return await update.message.reply_text("Replied message has no text.")

    await context.bot.edit_message_text(
        chat_id=f"@{CHANNEL_USERNAME}",
        message_id=post_id,
        text=new_text,
        reply_markup=default_keyboard()
    )

    await update.message.reply_text("✅ Text replaced successfully.")


# --- Replace Media ---
async def replace_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a media message.")

    if not context.args:
        return await update.message.reply_text("Use: /replace_media <channel_post_link>")

    post_id = extract_post_id(context.args[0])
    if not post_id:
        return await update.message.reply_text("Invalid channel post link.")

    msg = update.message.reply_to_message

    if msg.photo:
        file_id = msg.photo[-1].file_id
        await context.bot.edit_message_media(
            chat_id=f"@{CHANNEL_USERNAME}",
            message_id=post_id,
            media={"type": "photo", "media": file_id, "caption": msg.caption or ""}
        )

    elif msg.video:
        file_id = msg.video.file_id
        await context.bot.edit_message_media(
            chat_id=f"@{CHANNEL_USERNAME}",
            message_id=post_id,
            media={"type": "video", "media": file_id, "caption": msg.caption or ""}
        )
    else:
        return await update.message.reply_text("Reply must contain photo or video.")

    await update.message.reply_text("✅ Media replaced successfully.")


# --- Replace Buttons Only ---
async def replace_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Use: /replace_buttons <channel_post_link>")

    post_id = extract_post_id(context.args[0])
    if not post_id:
        return await update.message.reply_text("Invalid channel post link.")

    await context.bot.edit_message_reply_markup(
        chat_id=f"@{CHANNEL_USERNAME}",
        message_id=post_id,
        reply_markup=default_keyboard()
    )

    await update.message.reply_text("✅ Buttons replaced successfully.")


# --- Main Runner ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("replace_text", replace_text))
    app.add_handler(CommandHandler("replace_media", replace_media))
    app.add_handler(CommandHandler("replace_buttons", replace_buttons))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
