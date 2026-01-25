import os
import asyncio
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
    parts = post_link.split("/")
    chat_id = int("-100" + parts[-2])
    message_id = int(parts[-1])
    return chat_id, message_id

# =====================================================
#                     /START
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Post Manager Bot Online")

# =====================================================
#              /rep_btn
# =====================================================
async def rep_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text("Send channel post link to edit buttons.")
    user_data[update.effective_user.id] = {"step": "awaiting_post_link"}

# =====================================================
#                      /batch
# =====================================================
async def batch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text(
        "Send First link - Last link\nExample:\nhttps://t.me/c/123/10 - https://t.me/c/123/15"
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

    # ---------- BUTTON EDIT ----------
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_buttons"
        await update.message.reply_text("Send button layout now")
        return

    if step == "awaiting_buttons":
        link = user_data[user_id]["post_link"]
        chat_id, msg_id = extract_ids(link)
        keyboard = parse_buttons(update.message.text)

        await context.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=keyboard
        )
        message_buttons[msg_id] = keyboard
        await update.message.reply_text("✅ Buttons Updated")
        user_data[user_id] = {}
        return

    # ---------- BATCH STEP 1 ----------
    if step == "awaiting_batch_links":
        try:
            first, last = map(str.strip, update.message.text.split("-", 1))
            chat1, msg1 = extract_ids(first)
            chat2, msg2 = extract_ids(last)
        except:
            await update.message.reply_text("❌ Invalid format")
            return

        if chat1 != chat2:
            await update.message.reply_text("❌ Links must be same channel")
            return

        msg_ids = list(range(msg1, msg2 + 1))

        user_data[user_id] = {
            "step": "awaiting_mode",
            "chat_id": chat1,
            "msg_ids": msg_ids,
            "contents": []
        }

        await update.message.reply_text(
            f"Total {len(msg_ids)} posts found.\n\n"
            "Send:\n1 = Sequence Mode\n2 = Bulk Mode"
        )
        return

    # ---------- MODE SELECT ----------
    if step == "awaiting_mode":
        if update.message.text not in ["1", "2"]:
            await update.message.reply_text("Send only 1 or 2")
            return

        user_data[user_id]["mode"] = update.message.text
        user_data[user_id]["step"] = "collecting_media"

        total = len(user_data[user_id]["msg_ids"])

        if update.message.text == "1":
            await update.message.reply_text(f"Send media 1/{total}")
        else:
            await update.message.reply_text(
                f"Send {total} media now. After sending all type /done"
            )
        return

    # ---------- BULK DONE ----------
    if step == "collecting_media" and update.message.text == "/done":
        total = len(user_data[user_id]["msg_ids"])
        if len(user_data[user_id]["contents"]) != total:
            await update.message.reply_text("❌ Media count mismatch")
            return

        await process_batch(update, context, user_data[user_id])
        user_data[user_id] = {}
        return

    # ---------- COLLECT MEDIA ----------
    if step == "collecting_media":
        data = user_data[user_id]
        data["contents"].append(update.message)

        total = len(data["msg_ids"])
        done = len(data["contents"])

        if data["mode"] == "1":
            if done < total:
                await update.message.reply_text(f"Send media {done+1}/{total}")
                return
            else:
                await process_batch(update, context, data)
                user_data[user_id] = {}
                return
        else:
            await update.message.reply_text(f"Received {done}/{total}")
            return

# =====================================================
#              PROCESS BATCH
# =====================================================
async def process_batch(update, context, data):
    chat_id = data["chat_id"]
    msg_ids = data["msg_ids"]
    contents = data["contents"]

    progress = await update.message.reply_text(
        f"Processing 1/{len(msg_ids)}"
    )

    for i, (msg_id, content) in enumerate(zip(msg_ids, contents), start=1):
        await progress.edit_text(f"Processing {i}/{len(msg_ids)}")

        caption = content.caption or content.text or ""

        try:
            if content.photo:
                media = InputMediaPhoto(content.photo[-1].file_id, caption=caption)
                await context.bot.edit_message_media(chat_id, msg_id, media)

            elif content.video:
                media = InputMediaVideo(content.video.file_id, caption=caption)
                await context.bot.edit_message_media(chat_id, msg_id, media)

            elif content.document:
                media = InputMediaDocument(content.document.file_id, caption=caption)
                await context.bot.edit_message_media(chat_id, msg_id, media)

            elif content.animation:
                media = InputMediaAnimation(content.animation.file_id, caption=caption)
                await context.bot.edit_message_media(chat_id, msg_id, media)

            elif content.audio or content.voice:
                file_id = content.audio.file_id if content.audio else content.voice.file_id
                media = InputMediaAudio(file_id, caption=caption)
                await context.bot.edit_message_media(chat_id, msg_id, media)

            elif content.sticker:
                await context.bot.delete_message(chat_id, msg_id)
                await context.bot.send_sticker(chat_id, content.sticker.file_id)

            else:
                await context.bot.edit_message_text(chat_id, msg_id, caption)

        except Exception as e:
            await update.message.reply_text(f"❌ Error {msg_id}: {e}")

        await asyncio.sleep(0.4)

    await progress.edit_text("✅ Batch Replace Completed Successfully")

# =====================================================
#                       MAIN
# =====================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rep_btn", rep_btn))
    app.add_handler(CommandHandler("batch", batch_cmd))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
