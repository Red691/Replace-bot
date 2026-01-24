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
user_data = {}
message_buttons = {}  # message_id: InlineKeyboardMarkup
message_contents = {}  # message_id: original caption for replace

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
    """
    labels: list of button labels
    urls: dict mapping label->url
    pattern_text: pattern like '11\n2\n111'
    """
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
    await update.message.reply_text("Send channel post link to edit buttons or replace content.")
    user_data[update.effective_user.id] = {"step": "awaiting_post_link"}

# ---------- REPLACE ----------
async def replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "Send the post link you want to /replace.\nThen send new Text/Photo/Video.\nAfter that, send button labels and URLs and a pattern if you want buttons."
    )
    user_data[update.effective_user.id] = {"step": "awaiting_replace_link"}

# ---------- HANDLE MESSAGES ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    user_id = update.effective_user.id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]

    # ---- POST LINK FOR BUTTONS ----
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text(
            "Send button layout (optional):\nNew row = Enter\nSame row = Double Space"
        )
        return

    # ---- BUTTON EDIT FLOW ----
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
        user_data[user_id]["step"] = "awaiting_new_content"
        await update.message.reply_text("Send new Text/Photo/Video with optional caption.")
        return

    if step == "awaiting_new_content":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)
        if not chat_id:
            await update.message.reply_text("❌ Invalid post link.")
            return

        # Save new content temporarily
        user_data[user_id]["new_content"] = update.message
        user_data[user_id]["step"] = "awaiting_button_pattern"
        await update.message.reply_text(
            "Now send button labels and URLs in this format:\nLabel1 - URL1  Label2 - URL2\nAfter that, send button pattern like:\n11\n2\n111\nOr just send 'skip' to keep previous buttons."
        )
        return

    # ---- BUTTON PATTERN FLOW ----
    if step == "awaiting_button_pattern":
        # Check if user wants to skip
        text = update.message.text
        message_obj = user_data[user_id]["new_content"]
        chat_id, message_id = extract_ids(user_data[user_id]["post_link"])
        new_caption = message_obj.caption or message_obj.text or ""
        reply_markup = message_buttons.get(message_id)

        if text.lower() != "skip":
            try:
                # Parse labels and urls from first line(s)
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
                # Ask next message for pattern
                user_data[user_id]["labels"] = labels
                user_data[user_id]["urls"] = urls
                user_data[user_id]["step"] = "awaiting_pattern"
                await update.message.reply_text(
                    "Send pattern for buttons like:\n11\n2\n111"
                )
                return
            except:
                await update.message.reply_text("❌ Invalid format. Try again or send 'skip'.")
                return

        # If skip → just replace content with old buttons
        try:
            if message_obj.photo:
                file_id = message_obj.photo[-1].file_id
                media = InputMediaPhoto(media=file_id, caption=new_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )
            elif message_obj.video:
                file_id = message_obj.video.file_id
                media = InputMediaVideo(media=file_id, caption=new_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )
            elif message_obj.text:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_caption,
                    reply_markup=reply_markup
                )
            await update.message.reply_text("✅ Post replaced successfully!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

        user_data[user_id] = {}
        return

    # ---- AWAITING PATTERN ----
    if step == "awaiting_pattern":
        labels = user_data[user_id]["labels"]
        urls = user_data[user_id]["urls"]
        pattern_text = update.message.text
        message_obj = user_data[user_id]["new_content"]
        chat_id, message_id = extract_ids(user_data[user_id]["post_link"])
        reply_markup = buttons_from_pattern(labels, urls, pattern_text)

        new_caption = message_obj.caption or message_obj.text or ""

        try:
            if message_obj.photo:
                file_id = message_obj.photo[-1].file_id
                media = InputMediaPhoto(media=file_id, caption=new_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )
            elif message_obj.video:
                file_id = message_obj.video.file_id
                media = InputMediaVideo(media=file_id, caption=new_caption)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=reply_markup
                )
            elif message_obj.text:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_caption,
                    reply_markup=reply_markup
                )
            # Save buttons
            message_buttons[message_id] = reply_markup
            await update.message.reply_text("✅ Post replaced successfully with new buttons!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

        user_data[user_id] = {}
        return

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("replace", replace_cmd))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
