import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAnimation,
    InputMediaAudio
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

MAIN_CHANNEL = "https://t.me/YourChannel"
SUPPORT_GROUP = "https://t.me/YourSupportGroup"
OWNER_USERNAME = "@YourUsername"

# ===== DATA =====
user_data = {}
message_buttons = {}

# ---------- ADMIN CHECK ----------
def is_admin(update: Update):
    user = update.effective_user
    return user and int(user.id) == ADMIN_ID

# ---------- BUTTON PARSER ----------
def parse_buttons(text: str):
    keyboard = []
    rows = text.split("\n")
    for row in rows:
        row = row.strip()
        if not row:
            continue
        parts = row.split("  ")
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

# =====================================================
# /START
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro_text = (
        "Welcome to Post Manager Bot\n\n"
        "This bot helps manage Telegram channel posts.\n"
        "Replace media, captions, buttons, and more."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL)],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ])
    await update.message.reply_photo(
        photo="https://i.imgur.com/3ZQ3ZQp.jpg",
        caption=intro_text,
        reply_markup=keyboard
    )

# =====================================================
# CALLBACK QUERY HANDLER
# =====================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async def edit(text, keyboard):
        if query.message.photo or query.message.video:
            await query.edit_message_caption(caption=text, reply_markup=keyboard)
        else:
            await query.edit_message_text(text=text, reply_markup=keyboard)

    if query.data == "about":
        text = f"Owner: {OWNER_USERNAME}\nDeveloper: {OWNER_USERNAME}\n\nThis bot manages Telegram channel posts."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]])
        await edit(text, keyboard)
    elif query.data == "help":
        text = (
            "How To Use\n\n"
            "/rep_btn  - Edit only buttons of a post\n"
            "/replace  - Replace post media or text\n"
            "/batch  - Sequential batch replace\n"
            "/batch_same - Apply same content to multiple posts\n\n"
            "Admin only commands."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Replace Command Info", callback_data="cmd_replace")],
            [InlineKeyboardButton("💬 Support Group", url=SUPPORT_GROUP)],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
        await edit(text, keyboard)
    elif query.data == "home":
        text = "Welcome to Post Manager Bot\n\nReplace media, captions, buttons, and more."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL)],
            [InlineKeyboardButton("ℹ️ About", callback_data="about"),
             InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        await edit(text, keyboard)
    elif query.data == "cmd_replace":
        await query.answer("Use /replace command in chat", show_alert=True)

# =====================================================
# /rep_btn
# =====================================================
async def rep_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text("Send channel post link to edit buttons.")
    user_data[update.effective_user.id] = {"step": "awaiting_post_link"}

# =====================================================
# /replace
# =====================================================
async def replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text("Send the post link you want to replace.")
    user_data[update.effective_user.id] = {"step": "awaiting_replace_link"}

# =====================================================
# /batch
# =====================================================
async def batch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "Send first and last post links separated by dash (-)\nExample:\nhttps://t.me/c/123/50 - https://t.me/c/123/60"
    )
    user_data[update.effective_user.id] = {"step": "awaiting_batch_links"}

# =====================================================
# /batch_same
# =====================================================
async def batch_same_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "Send first and last post links separated by dash (-)\nExample:\nhttps://t.me/c/123/50 - https://t.me/c/123/60"
    )
    user_data[update.effective_user.id] = {"step": "awaiting_batch_same_links"}

# =====================================================
# MAIN MESSAGE HANDLER
# =====================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    user_id = update.effective_user.id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]

    # ----- BUTTON EDIT -----
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text("Send button layout:\nLabel - URL\nDouble space = same row\nEnter = new row")
        return

    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]
        keyboard = parse_buttons(update.message.text)
        chat_id, message_id = extract_ids(post_link)
        try:
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
            if keyboard:
                message_buttons[message_id] = keyboard
            await update.message.reply_text("✅ Buttons updated!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
        user_data[user_id] = {}
        return

    # ----- REPLACE -----
    if step == "awaiting_replace_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_new_file"
        await update.message.reply_text("Send new content (Photo/Video/Document/Animation/Audio/Text) or type skip")
        return

    if step == "awaiting_new_file":
        content = parse_message_content(update.message)
        user_data[user_id]["new_content"] = content
        user_data[user_id]["step"] = "awaiting_new_buttons"
        await update.message.reply_text("Send new button layout OR type skip")
        return

    if step == "awaiting_new_buttons":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)
        new_content = user_data[user_id]["new_content"]
        if update.message.text.lower() == "skip":
            reply_markup = message_buttons.get(message_id, None)
        else:
            new_buttons = parse_buttons(update.message.text)
            reply_markup = new_buttons or message_buttons.get(message_id, None)
        await edit_message(chat_id, message_id, new_content, reply_markup, context)
        if reply_markup:
            message_buttons[message_id] = reply_markup
        await update.message.reply_text("✅ Post replaced successfully!")
        user_data[user_id] = {}
        return

    # ----- BATCH -----
    if step == "awaiting_batch_links":
        try:
            first_link, last_link = map(str.strip, update.message.text.split("-", 1))
        except:
            await update.message.reply_text("❌ Invalid format. Send like:\nlink1 - link2")
            return
        first_chat, first_msg = extract_ids(first_link)
        last_chat, last_msg = extract_ids(last_link)
        if first_chat != last_chat:
            await update.message.reply_text("❌ First and last messages must be from the same chat")
            return
        msg_ids = list(range(first_msg, last_msg + 1))
        user_data[user_id]["msg_ids"] = msg_ids
        user_data[user_id]["chat_id"] = first_chat
        user_data[user_id]["step"] = "awaiting_batch_content"
        user_data[user_id]["batch_contents"] = []
        await update.message.reply_text(
            f"Send new content for {len(msg_ids)} messages sequentially, or type skip for each"
        )
        return

    if step == "awaiting_batch_content":
        content = parse_message_content(update.message)
        user_data[user_id]["batch_contents"].append(content)
        # check if all messages received
        if len(user_data[user_id]["batch_contents"]) < len(user_data[user_id]["msg_ids"]):
            await update.message.reply_text("Send next content or type skip")
            return
        user_data[user_id]["step"] = "awaiting_batch_buttons"
        await update.message.reply_text("Send new button layout OR type skip")
        return

    if step == "awaiting_batch_buttons":
        chat_id = user_data[user_id]["chat_id"]
        msg_ids = user_data[user_id]["msg_ids"]
        contents = user_data[user_id]["batch_contents"]
        if update.message.text.lower() == "skip":
            reply_markup_list = [message_buttons.get(msg_id, None) for msg_id in msg_ids]
        else:
            new_buttons = parse_buttons(update.message.text)
            reply_markup_list = [new_buttons or message_buttons.get(msg_id, None) for msg_id in msg_ids]
        for msg_id, content, reply_markup in zip(msg_ids, contents, reply_markup_list):
            await edit_message(chat_id, msg_id, content, reply_markup, context)
            if reply_markup:
                message_buttons[msg_id] = reply_markup
        await update.message.reply_text("✅ Batch replace completed!")
        user_data[user_id] = {}
        return

# =====================================================
# HELPERS
# =====================================================
def parse_message_content(message):
    if message.text:
        return {"type": "text", "text": message.text}
    elif message.photo:
        return {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption or ""}
    elif message.video:
        return {"type": "video", "file_id": message.video.file_id, "caption": message.caption or ""}
    elif message.document:
        return {"type": "document", "file_id": message.document.file_id, "caption": message.caption or ""}
    elif message.audio:
        return {"type": "audio", "file_id": message.audio.file_id, "caption": message.caption or ""}
    elif message.animation:
        return {"type": "animation", "file_id": message.animation.file_id, "caption": message.caption or ""}
    else:
        return {"type": "skip"}

async def edit_message(chat_id, message_id, content, reply_markup, context):
    try:
        if not content or content["type"] == "skip":
            await context.bot.edit_message_reply_markup(chat_id, message_id, reply_markup=reply_markup)
            return
        if content["type"] == "text":
            await context.bot.edit_message_text(chat_id, message_id, content["text"], reply_markup=reply_markup)
        elif content["type"] == "photo":
            media = InputMediaPhoto(media=content["file_id"], caption=content["caption"])
            await context.bot.edit_message_media(chat_id, message_id, media=media, reply_markup=reply_markup)
        elif content["type"] == "video":
            media = InputMediaVideo(media=content["file_id"], caption=content["caption"])
            await context.bot.edit_message_media(chat_id, message_id, media=media, reply_markup=reply_markup)
        elif content["type"] == "document":
            media = InputMediaDocument(media=content["file_id"], caption=content["caption"])
            await context.bot.edit_message_media(chat_id, message_id, media=media, reply_markup=reply_markup)
        elif content["type"] == "audio":
            media = InputMediaAudio(media=content["file_id"], caption=content["caption"])
            await context.bot.edit_message_media(chat_id, message_id, media=media, reply_markup=reply_markup)
        elif content["type"] == "animation":
            media = InputMediaAnimation(media=content["file_id"], caption=content["caption"])
            await context.bot.edit_message_media(chat_id, message_id, media=media, reply_markup=reply_markup)
    except Exception as e:
        print(f"❌ Failed to edit message {message_id}: {e}")

# =====================================================
# MAIN
# =====================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rep_btn", rep_btn))
    app.add_handler(CommandHandler("replace", replace_cmd))
    app.add_handler(CommandHandler("batch", batch_cmd))
    app.add_handler(CommandHandler("batch_same", batch_same_cmd))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
