import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo
)
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # Heroku Config Var for admin

# ----- TEMP DATA -----
user_data = {}          # user_id -> step info
message_buttons = {}    # message_id -> InlineKeyboardMarkup

# ---------- ADMIN CHECK ----------
def is_admin(update: Update):
    user = update.effective_user
    return user and int(user.id) == ADMIN_ID

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
            label, url = label.strip(), url.strip()
            if not url.startswith("http"):
                continue
            row_buttons.append(InlineKeyboardButton(label, url=url))
        if row_buttons:
            keyboard.append(row_buttons)
    return InlineKeyboardMarkup(keyboard) if keyboard else None

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
    await update.message.reply_text("Send channel post link to edit buttons.")
    user_data[update.effective_user.id] = {"step": "awaiting_post_link"}

# ---------- REPLACE ----------
async def replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "Send the post link you want to /replace."
    )
    user_data[update.effective_user.id] = {"step": "awaiting_replace_link"}

# ---------- MAIN HANDLER ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    user_id = update.effective_user.id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]

    # ---- BUTTON EDIT FLOW ----
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text(
            "Send button layout (if any):\n\nNew row = Enter\nSame row = Double Space"
        )
        return

    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]
        keyboard = parse_buttons(update.message.text)
        chat_id, message_id = extract_ids(post_link)
        if not chat_id:
            await update.message.reply_text("❌ Invalid post link.")
            return
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            if keyboard:
                message_buttons[message_id] = keyboard
            await update.message.reply_text("✅ Buttons updated successfully!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
        user_data[user_id] = {}
        return

    # ---- REPLACE FLOW ----
    if step == "awaiting_replace_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_new_file"
        await update.message.reply_text(
            "Step 1: Send the new file (Photo/Video) OR text with original caption."
        )
        return

    if step == "awaiting_new_file":
        # Save the new content temporarily
        user_data[user_id]["new_content"] = update.message
        user_data[user_id]["step"] = "awaiting_new_buttons"
        await update.message.reply_text(
            "Step 2: Send new inline buttons (if any) for this post.\n\n"
            "Format:\nLabel - URL (Double space for same row, Enter for new row)"
        )
        return

    if step == "awaiting_new_buttons":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)
        if not chat_id:
            await update.message.reply_text("❌ Invalid post link.")
            user_data[user_id] = {}
            return

        new_msg = user_data[user_id].get("new_content")
        new_buttons = parse_buttons(update.message.text)
        reply_markup = new_buttons or message_buttons.get(message_id, None)

        try:
            original_caption = ""
            if new_msg.photo or new_msg.video:
                original_caption = new_msg.caption or ""
            elif new_msg.text:
                original_caption = new_msg.text or ""

            # --- PHOTO ---
            if new_msg.photo:
                file_id = new_msg.photo[-1].file_id
                media = InputMediaPhoto(media=file_id, caption=original_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )
            # --- VIDEO ---
            elif new_msg.video:
                file_id = new_msg.video.file_id
                media = InputMediaVideo(media=file_id, caption=original_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )
            # --- TEXT ---
            elif new_msg.text:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=original_caption,
                    reply_markup=reply_markup
                )

            # Save buttons for future replaces
            if reply_markup:
                message_buttons[message_id] = reply_markup

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
