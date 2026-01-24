import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))  # <-- Add this in Heroku Config Vars

user_data = {}

# ---------- ADMIN CHECK ----------
def is_admin(update: Update):
    return update.effective_user.id == ADMIN_ID


# ---------- BUTTON PARSER ----------
def parse_buttons(text: str):
    keyboard = []
    rows = text.split("\n")   # Enter = new row

    for row in rows:
        row = row.strip()
        if not row:
            continue

        parts = row.split("  ")  # double space = same row
        row_buttons = []

        for part in parts:
            part = part.strip()
            if "-" not in part:
                continue

            label, url = part.split("-", 1)
            label = label.strip()
            url = url.strip()

            if not url.startswith("http"):
                continue

            row_buttons.append(InlineKeyboardButton(label, url=url))

        if row_buttons:
            keyboard.append(row_buttons)

    return keyboard


# ---------- LINK EXTRACT ----------
def extract_ids(post_link: str):
    if "t.me/c/" not in post_link:
        return None, None
    parts = post_link.split("/")
    chat_id = int("-100" + parts[-2])
    message_id = int(parts[-1])
    return chat_id, message_id


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return

    await update.message.reply_text("Send channel post link to add/replace buttons.")
    user_data[update.effective_user.id] = {"step": "awaiting_post_link"}


# ---------- REPLACE ----------
async def replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return

    await update.message.reply_text("Send channel post link you want to REPLACE.")
    user_data[update.effective_user.id] = {"step": "awaiting_replace_link"}


# ---------- MAIN MESSAGE HANDLER ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    user_id = update.effective_user.id

    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]
    text = update.message.text if update.message else None

    # ---- BUTTON FLOW ----
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text(
            "Send button layout.\n\nNew row = Enter\nSame row = Double Space"
        )
        return

    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]
        keyboard = parse_buttons(text)

        if not keyboard:
            await update.message.reply_text("❌ No valid buttons found.")
            return

        chat_id, message_id = extract_ids(post_link)
        if not chat_id:
            await update.message.reply_text("❌ Invalid post link.")
            return

        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await update.message.reply_text("✅ Buttons updated successfully!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

        user_data[user_id] = {}
        return

    # ---- REPLACE FLOW ----
    if step == "awaiting_replace_link":
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_new_content"
        await update.message.reply_text("Send new text OR photo OR video.")
        return

    if step == "awaiting_new_content":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)

        if not chat_id:
            await update.message.reply_text("❌ Invalid post link.")
            return

        try:
            # Replace Text
            if update.message.text:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=update.message.text
                )

            # Replace Photo
            elif update.message.photo:
                file_id = update.message.photo[-1].file_id
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=InputMediaPhoto(file_id)
                )

            # Replace Video
            elif update.message.video:
                file_id = update.message.video.file_id
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=InputMediaVideo(file_id)
                )

            await update.message.reply_text("✅ Post replaced successfully!")

        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

        user_data[user_id] = {}


# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("replace", replace_cmd))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
