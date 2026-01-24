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
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # Heroku Config Var or direct ID

# ----- TEMP DATA -----
user_data = {}          # Tracks user step
message_buttons = {}    # message_id: InlineKeyboardMarkup

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

# ---------- BUTTON PATTERN GENERATOR ----------
def buttons_from_pattern(labels, urls, pattern_text):
    keyboard = []
    index = 0
    for line in pattern_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        row_buttons = []
        for _ in line:
            if index >= len(labels):
                break
            label = labels[index]
            url = urls.get(label)
            if url:
                row_buttons.append(InlineKeyboardButton(label, url=url))
            index += 1
        if row_buttons:
            keyboard.append(row_buttons)
    return InlineKeyboardMarkup(keyboard)

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
    await update.message.reply_text("Use /replace to replace post content or /format to generate buttons.")

# ---------- REPLACE ----------
async def replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "Send the post link you want to /replace. Then send new content (photo/video/text). Original caption will be used, button captions removed."
    )
    user_data[update.effective_user.id] = {"step": "awaiting_replace_link"}

# ---------- FORMAT ----------
async def format_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "Send button labels + URLs in format:\nLabel1 - URL1  Label2 - URL2 ...\nThen send the pattern, e.g.:\n11\n2\n111"
    )
    user_data[update.effective_user.id] = {"step": "awaiting_format_labels"}

# ---------- MAIN HANDLER ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    user_id = update.effective_user.id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]
    text = update.message.text if update.message else ""

    # ---- REPLACE FLOW ----
    if step == "awaiting_replace_link":
        user_data[user_id]["post_link"] = text
        user_data[user_id]["step"] = "awaiting_new_content"
        await update.message.reply_text("Send new Text/Photo/Video for replacement.")
        return

    if step == "awaiting_new_content":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)
        if not chat_id:
            await update.message.reply_text("❌ Invalid post link.")
            return

        try:
            reply_markup = message_buttons.get(message_id, None)
            original_caption = update.message.caption or update.message.text or ""

            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                media = InputMediaPhoto(media=file_id, caption=original_caption)
                await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=reply_markup)
            elif update.message.video:
                file_id = update.message.video.file_id
                media = InputMediaVideo(media=file_id, caption=original_caption)
                await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=reply_markup)
            elif update.message.text:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=original_caption, reply_markup=reply_markup)

            await update.message.reply_text("✅ Post replaced successfully! Buttons preserved, button caption removed.")

        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

        user_data[user_id] = {}
        return

    # ---- FORMAT FLOW ----
    if step == "awaiting_format_labels":
        try:
            # Parse labels and urls
            lines = text.split("\n")
            labels = []
            urls = {}
            for line in lines:
                parts = line.split("  ")
                for part in parts:
                    if "-" in part:
                        label, url = part.split("-",1)
                        labels.append(label.strip())
                        urls[label.strip()] = url.strip()
            user_data[user_id]["labels"] = labels
            user_data[user_id]["urls"] = urls
            user_data[user_id]["step"] = "awaiting_pattern"
            await update.message.reply_text("Now send pattern like:\n11\n2\n111")
        except:
            await update.message.reply_text("❌ Invalid format, try again.")
        return

    if step == "awaiting_pattern":
        labels = user_data[user_id]["labels"]
        urls = user_data[user_id]["urls"]
        pattern_text = text
        keyboard = buttons_from_pattern(labels, urls, pattern_text)
        await update.message.reply_text("✅ Buttons generated successfully!", reply_markup=keyboard)
        user_data[user_id] = {}
        return

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("replace", replace_cmd))
    app.add_handler(CommandHandler("format", format_cmd))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
