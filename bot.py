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
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# ----- TEMP DATA -----
user_data = {}
message_buttons = {}


# ---------- ADMIN CHECK ----------
def is_admin(update: Update):
    user = update.effective_user
    return user and int(user.id) == ADMIN_ID


# ---------- NEW BUTTON PARSER ----------
# Each line = one row
# Each button separated by single space
# Format: Label-https://link
def parse_buttons(text: str):
    keyboard = []
    rows = text.split("\n")

    for row in rows:
        row = row.strip()
        if not row:
            continue

        parts = row.split()  # Single space separates buttons
        row_buttons = []

        for part in parts:
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
    text = update.message.text if update.message else None

    # ---- BUTTON EDIT FLOW ----
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text(
            "Send button layout:\nEach line = one row\nButtons separated by space"
        )
        return

    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]
        keyboard = parse_buttons(text)
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
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_new_content"
        await update.message.reply_text(
            "Send new Text / Photo / Video. Caption me buttons bhi likh sakte ho."
        )
        return

    if step == "awaiting_new_content":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)

        if not chat_id:
            await update.message.reply_text("❌ Invalid post link.")
            return

        try:
            new_buttons = None
            if update.message.caption:
                new_buttons = parse_buttons(update.message.caption)
            elif update.message.text:
                new_buttons = parse_buttons(update.message.text)

            reply_markup = new_buttons or message_buttons.get(message_id, None)
            new_caption = update.message.caption or update.message.text or ""

            # --- PHOTO ---
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                media = InputMediaPhoto(media=file_id, caption=new_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )

            # --- VIDEO ---
            elif update.message.video:
                file_id = update.message.video.file_id
                media = InputMediaVideo(media=file_id, caption=new_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )

            # --- TEXT ---
            elif update.message.text:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_caption,
                    reply_markup=reply_markup
                )

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
