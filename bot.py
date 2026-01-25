import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    InputFile
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

# ---------- RANGE GENERATOR ----------
def generate_message_ids(first_id, last_id):
    if first_id > last_id:
        first_id, last_id = last_id, first_id
    return list(range(first_id, last_id + 1))

# =====================================================
#                     /START
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro_text = (
        "Welcome to Post Manager Bot\n\n"
        "This bot helps manage Telegram channel posts.\n"
        "Replace media, captions, files, and buttons easily."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL)],
        [
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ])
    await update.message.reply_photo(
        photo="https://i.imgur.com/3ZQ3ZQp.jpg",
        caption=intro_text,
        reply_markup=keyboard
    )

# =====================================================
#              CALLBACK QUERY HANDLER
# =====================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    async def edit(text, keyboard):
        if query.message.photo:
            await query.edit_message_caption(caption=text, reply_markup=keyboard)
        else:
            await query.edit_message_text(text=text, reply_markup=keyboard)

    if query.data == "about":
        text = f"Owner: {OWNER_USERNAME}\nDeveloper: {OWNER_USERNAME}\n\nThis bot manages Telegram posts."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]])
        await edit(text, keyboard)
    elif query.data == "help":
        text = (
            "Commands:\n"
            "/rep_btn - Edit buttons\n"
            "/replace - Replace a post\n"
            "/batch - Replace multiple posts sequentially\n\n"
            "Admin only."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Replace Info", callback_data="cmd_replace")],
            [InlineKeyboardButton("💬 Support Group", url=SUPPORT_GROUP)],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
        await edit(text, keyboard)
    elif query.data == "home":
        text = "Welcome to Post Manager Bot\nManage posts easily."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL)],
            [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        await edit(text, keyboard)
    elif query.data == "cmd_replace":
        await query.answer("Use /replace command in chat", show_alert=True)

# =====================================================
#              /rep_btn
# =====================================================
async def rep_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text("Send channel post link to edit buttons.")
    user_data[update.effective_user.id] = {"step": "awaiting_post_link"}

# =====================================================
#                      /replace
# =====================================================
async def replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text("Send the post link you want to replace.")
    user_data[update.effective_user.id] = {"step": "awaiting_replace_link"}

# =====================================================
#                      /batch
# =====================================================
async def batch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "Send FIRST and LAST post links separated by a dash (-)\n"
        "Example:\nhttps://t.me/c/123/50 - https://t.me/c/123/59"
    )
    user_data[update.effective_user.id] = {"step": "awaiting_batch_links"}

# =====================================================
#                  MAIN MESSAGE HANDLER
# =====================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    user_id = update.effective_user.id
    if user_id not in user_data:
        return
    step = user_data[user_id]["step"]

    # ---- BUTTON EDIT ----
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text(
            "Send button layout:\nLabel - URL\nDouble space = same row\nEnter = new row"
        )
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

    # ---- REPLACE SINGLE ----
    if step == "awaiting_replace_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_new_file"
        await update.message.reply_text("Send new Photo / Video / Text / File or type skip")
        return
    if step == "awaiting_new_file":
        if update.message.text and update.message.text.lower() == "skip":
            user_data[user_id]["new_content"] = None
        else:
            user_data[user_id]["new_content"] = update.message
        user_data[user_id]["step"] = "awaiting_new_buttons"
        await update.message.reply_text("Send new button layout OR type skip")
        return
    if step == "awaiting_new_buttons":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)
        new_msg = user_data[user_id]["new_content"]
        if update.message.text.lower() == "skip":
            reply_markup = message_buttons.get(message_id, None)
        else:
            new_buttons = parse_buttons(update.message.text)
            reply_markup = new_buttons or message_buttons.get(message_id, None)
        try:
            if new_msg:
                if new_msg.photo:
                    media = InputMediaPhoto(media=new_msg.photo[-1].file_id, caption=new_msg.caption or "")
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=reply_markup)
                elif new_msg.video:
                    media = InputMediaVideo(media=new_msg.video.file_id, caption=new_msg.caption or "")
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=reply_markup)
                elif new_msg.document:
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=InputMediaPhoto(media=new_msg.document.file_id, caption=new_msg.caption or ""), reply_markup=reply_markup)
                else:
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_msg.text or "", reply_markup=reply_markup)
            else:
                await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
            if reply_markup:
                message_buttons[message_id] = reply_markup
            await update.message.reply_text("✅ Post replaced successfully!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
        user_data[user_id] = {}
        return

    # ---- BATCH REPLACE ----
    if step == "awaiting_batch_links":
        try:
            first_link, last_link = map(str.strip, update.message.text.split("-", 1))
        except:
            await update.message.reply_text("❌ Invalid format. Send like:\nlink1 - link2")
            return
        f_chat, f_id = extract_ids(first_link)
        l_chat, l_id = extract_ids(last_link)
        ids_list = generate_message_ids(f_id, l_id)
        if f_chat != l_chat:
            await update.message.reply_text("❌ Links must belong to same channel.")
            return
        user_data[user_id]["chat_id"] = f_chat
        user_data[user_id]["msg_ids"] = ids_list
        user_data[user_id]["step"] = "awaiting_batch_content"
        await update.message.reply_text(
            f"Send {len(ids_list)} content messages (Photo/Video/Text/File) sequentially or type skip for all"
        )
        return

    if step == "awaiting_batch_content":
        msg_ids = user_data[user_id]["msg_ids"]
        contents = []
        if update.message.text and update.message.text.lower() == "skip":
            contents = [None]*len(msg_ids)
        else:
            # If user sends media group, collect all
            if update.message.media_group_id:
                contents = update.message.effective_attachment  # Will handle single or multiple
            else:
                contents.append(update.message)
        if len(contents) != len(msg_ids):
            await update.message.reply_text(f"❌ Number of contents ({len(contents)}) doesn't match messages ({len(msg_ids)}).")
            return
        user_data[user_id]["new_contents"] = contents
        user_data[user_id]["step"] = "awaiting_batch_buttons"
        await update.message.reply_text("Send new button layout OR type skip")
        return

    if step == "awaiting_batch_buttons":
        chat_id = user_data[user_id]["chat_id"]
        msg_ids = user_data[user_id]["msg_ids"]
        contents = user_data[user_id]["new_contents"]
        if update.message.text.lower() == "skip":
            reply_markup = None
        else:
            reply_markup = parse_buttons(update.message.text)
        for i, msg_id in enumerate(msg_ids):
            new_msg = contents[i]
            try:
                if new_msg:
                    if new_msg.photo:
                        media = InputMediaPhoto(media=new_msg.photo[-1].file_id, caption=new_msg.caption or "")
                        await context.bot.edit_message_media(chat_id=chat_id, message_id=msg_id, media=media, reply_markup=reply_markup)
                    elif new_msg.video:
                        media = InputMediaVideo(media=new_msg.video.file_id, caption=new_msg.caption or "")
                        await context.bot.edit_message_media(chat_id=chat_id, message_id=msg_id, media=media, reply_markup=reply_markup)
                    elif new_msg.document:
                        await context.bot.edit_message_media(chat_id=chat_id, message_id=msg_id, media=InputMediaPhoto(media=new_msg.document.file_id, caption=new_msg.caption or ""), reply_markup=reply_markup)
                    else:
                        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_msg.text or "", reply_markup=reply_markup)
                else:
                    await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup)
                if reply_markup:
                    message_buttons[msg_id] = reply_markup
            except Exception as e:
                await update.message.reply_text(f"❌ Failed msg {msg_id}: {e}")
        await update.message.reply_text("✅ Batch replace done successfully!")
        user_data[user_id] = {}
        return

# =====================================================
#                       MAIN
# =====================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rep_btn", rep_btn))
    app.add_handler(CommandHandler("replace", replace_cmd))
    app.add_handler(CommandHandler("batch", batch_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
