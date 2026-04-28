import os
import asyncio
import sqlite3
import re
from urllib.parse import urlparse
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

from flask import Flask
import threading

# ===== FLASK WEB SERVER (for hosting platforms) =====
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = list(map(int, os.environ.get("ADMIN_ID", "").split(","))) if os.environ.get("ADMIN_ID") else []

MAIN_CHANNEL = os.environ.get("MAIN_CHANNEL", "https://t.me/YourChannel")
SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "https://t.me/YourSupportGroup")
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "@YourUsername")

# ===== DATABASE SETUP =====
DB_FILE = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Templates table
    c.execute('''CREATE TABLE IF NOT EXISTS templates (
        user_id INTEGER PRIMARY KEY,
        template_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Message buttons cache
    c.execute('''CREATE TABLE IF NOT EXISTS message_buttons (
        message_id INTEGER PRIMARY KEY,
        chat_id INTEGER,
        button_data TEXT
    )''')
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_FILE)

# ===== TEMPLATE FUNCTIONS =====
def save_template(user_id: int, template_text: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO templates (user_id, template_text) 
                 VALUES (?, ?)''', (user_id, template_text))
    conn.commit()
    conn.close()

def get_template(user_id: int) -> str:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT template_text FROM templates WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def delete_template(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM templates WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# ===== BUTTON TEMPLATE PARSER =====
def is_valid_url(url: str) -> bool:
    """Validate URL format"""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)
    except:
        return False

def parse_template_buttons(template_text: str, link_value: str = None, max_per_row: int = 8) -> InlineKeyboardMarkup:
    """
    Parse button template with format:
    Line 1: Button1 - {link} | Button2 - {link}
    Line 2: Button3 - https://example.com
    
    Each line = new row
    | = same row separator
    - = button name/url separator
    {link} = replaced with link_value
    """
    keyboard = []
    
    lines = template_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        row_buttons = []
        # Split by | for same row buttons
        button_parts = [p.strip() for p in line.split('|')]
        
        for part in button_parts:
            if ' - ' not in part:
                continue
                
            # Split by first occurrence of " - "
            name, url = part.split(' - ', 1)
            name = name.strip()
            url = url.strip()
            
            # Replace {link} placeholder
            if '{link}' in url and link_value:
                url = url.replace('{link}', link_value)
            
            # Skip if URL is invalid (unless it's a template without link provided)
            if '{link}' in url and not link_value:
                continue  # Skip buttons with unresolved {link}
            
            if not is_valid_url(url):
                continue
                
            if name and url:
                row_buttons.append(InlineKeyboardButton(name, url=url))
        
        # Add row if valid buttons exist
        if row_buttons:
            # Limit buttons per row to Telegram safe limit
            for i in range(0, len(row_buttons), max_per_row):
                keyboard.append(row_buttons[i:i + max_per_row])
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def parse_legacy_buttons(text: str) -> InlineKeyboardMarkup:
    """Legacy parser for backward compatibility (double space = same row)"""
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
            if " - " not in part:
                continue
            label, url = part.split(" - ", 1)
            label, url = label.strip(), url.strip()
            if not is_valid_url(url):
                continue
            row_buttons.append(InlineKeyboardButton(label, url=url))
        if row_buttons:
            keyboard.append(row_buttons)
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ===== LINK EXTRACT =====
def extract_ids(post_link: str):
    if "t.me/c/" not in post_link:
        return None, None
    try:
        parts = post_link.split("/")
        chat_id = int("-100" + parts[-2])
        message_id = int(parts[-1])
        return chat_id, message_id
    except:
        return None, None

# ===== ADMIN CHECK =====
def is_admin(update: Update):
    user = update.effective_user
    return user and int(user.id) in ADMIN_ID

# ===== USER DATA (for conversation flow) =====
user_data = {}

# =====================================================
# /START
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro_text = (
        "🤖 <b>Welcome to Post Manager Bot</b>\n\n"
        "This bot helps manage Telegram channel posts efficiently.\n"
        "Replace media, captions, buttons, and more with ease!\n\n"
        "🆕 <b>New Feature:</b> Button Templates!\n"
        "Use /setbtns to create reusable button templates."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL)],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ])
    await update.message.reply_photo(
        photo="https://i.imgur.com/3ZQ3ZQp.jpg",
        caption=intro_text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

# =====================================================
# CALLBACK QUERY HANDLER
# =====================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async def edit(text, keyboard):
        if query.message.photo or query.message.video:
            await query.edit_message_caption(caption=text, reply_markup=keyboard, parse_mode='HTML')
        else:
            await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='HTML')

    if query.data == "about":
        text = f"👤 <b>Owner:</b> {OWNER_USERNAME}\n💻 <b>Developer:</b> {OWNER_USERNAME}\n\nThis bot manages Telegram channel posts with advanced features."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]])
        await edit(text, keyboard)
    elif query.data == "help":
        text = (
            "📖 <b>How To Use</b>\n\n"
            "<code>/setbtns</code> - Set button template\n"
            "<code>/mybtns</code> - View your template\n"
            "<code>/delbtns</code> - Delete template\n\n"
            "<code>/rep_btn &lt;link&gt;</code> - Edit buttons using template\n"
            "<code>/replace</code> - Replace post media/text\n"
            "<code>/batch</code> - Batch replace (different content)\n"
            "<code>/batch_same</code> - Batch replace (same content)\n\n"
            "⚠️ Admin only commands."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Replace Command Info", callback_data="cmd_replace")],
            [InlineKeyboardButton("💬 Support Group", url=SUPPORT_GROUP)],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
        await edit(text, keyboard)
    elif query.data == "home":
        text = "🤖 <b>Welcome to Post Manager Bot</b>\n\nReplace media, captions, buttons, and more."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL)],
            [InlineKeyboardButton("ℹ️ About", callback_data="about"),
             InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        await edit(text, keyboard)
    elif query.data == "cmd_replace":
        await query.answer("Use /replace command in chat", show_alert=True)

# =====================================================
# /SETBTNS - Set Button Template
# =====================================================
async def setbtns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ <b>Access Denied</b>", parse_mode='HTML')
        return
    
    # Check if template provided with command
    if context.args:
        template_text = ' '.join(context.args)
        save_template(update.effective_user.id, template_text)
        await update.message.reply_text(
            "✅ <b>Button Template Saved!</b>\n\n"
            f"<pre>{template_text}</pre>\n\n"
            "Use <code>/mybtns</code> to view or <code>/delbtns</code> to delete.",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text(
        "📝 <b>Send your button template</b>\n\n"
        "<b>Format:</b>\n"
        "<code>Button Name - {link} | Button2 - {link}</code>\n"
        "<code>Button3 - https://example.com</code>\n\n"
        "• Each line = new row\n"
        "• <code>|</code> = same row separator\n"
        "• <code>{link}</code> = will be replaced with post link\n"
        "• <code> - </code> = separator between name and URL\n\n"
        "<b>Example:</b>\n"
        "<pre>Watch Now - {link} | Download - {link}\n"
        "Trailer - https://youtube.com/trailer</pre>",
        parse_mode='HTML'
    )
    user_data[update.effective_user.id] = {"step": "awaiting_template"}

# =====================================================
# /MYBTNS - View Template
# =====================================================
async def mybtns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ <b>Access Denied</b>", parse_mode='HTML')
        return
    
    template = get_template(update.effective_user.id)
    if not template:
        await update.message.reply_text(
            "❌ <b>No template found!</b>\n\n"
            "Use <code>/setbtns</code> to create one.",
            parse_mode='HTML'
        )
        return
    
    # Preview with dummy link
    preview_markup = parse_template_buttons(template, "https://example.com")
    
    await update.message.reply_text(
        "📋 <b>Your Current Template:</b>\n\n"
        f"<pre>{template}</pre>\n\n"
        "👇 <b>Preview (with example link):</b>",
        parse_mode='HTML',
        reply_markup=preview_markup
    )

# =====================================================
# /DELBTNS - Delete Template
# =====================================================
async def delbtns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ <b>Access Denied</b>", parse_mode='HTML')
        return
    
    delete_template(update.effective_user.id)
    await update.message.reply_text(
        "🗑️ <b>Template deleted successfully!</b>\n\n"
        "Use <code>/setbtns</code> to create a new one.",
        parse_mode='HTML'
    )

# =====================================================
# /REP_BTN <link> - Quick Button Replace with Template
# =====================================================
async def rep_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ <b>Access Denied</b>", parse_mode='HTML')
        return
    
    user_id = update.effective_user.id
    template = get_template(user_id)
    
    # Check if link provided with command
    if context.args:
        post_link = context.args[0]
        chat_id, message_id = extract_ids(post_link)
        
        if not chat_id or not message_id:
            await update.message.reply_text("❌ <b>Invalid post link!</b>\nFormat: <code>https://t.me/c/123456/789</code>", parse_mode='HTML')
            return
        
        if not template:
            await update.message.reply_text(
                "❌ <b>No template found!</b>\n\n"
                "Use <code>/setbtns</code> to set a button template first.",
                parse_mode='HTML'
            )
            return
        
        # Generate buttons with link replacement
        keyboard = parse_template_buttons(template, post_link)
        
        if not keyboard:
            await update.message.reply_text("❌ <b>No valid buttons generated!</b>\nCheck your template.", parse_mode='HTML')
            return
        
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            
            # Save to cache
            conn = get_db()
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO message_buttons (message_id, chat_id, button_data) 
                         VALUES (?, ?, ?)''', (message_id, chat_id, template))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                "✅ <b>Buttons updated successfully!</b>\n\n"
                f"🔗 Post: <code>{post_link}</code>",
                parse_mode='HTML'
            )
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode='HTML')
        return
    
    # No link provided - start conversation flow
    if not template:
        await update.message.reply_text(
            "❌ <b>No template found!</b>\n\n"
            "Use <code>/setbtns</code> to set a button template first.",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text(
        "🔗 <b>Send the post link</b> to apply your template.\n\n"
        f"📋 Current template:\n<pre>{template}</pre>",
        parse_mode='HTML'
    )
    user_data[user_id] = {"step": "awaiting_post_link_for_template"}

# =====================================================
# /REPLACE
# =====================================================
async def replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ <b>Access Denied</b>", parse_mode='HTML')
        return
    await update.message.reply_text("🔗 Send the post link you want to replace.")
    user_data[update.effective_user.id] = {"step": "awaiting_replace_link"}

# =====================================================
# /BATCH
# =====================================================
async def batch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ <b>Access Denied</b>", parse_mode='HTML')
        return
    await update.message.reply_text(
        "🔗 Send first and last post links separated by dash (-)\n"
        "<b>Example:</b>\n<code>https://t.me/c/123/50 - https://t.me/c/123/55</code>",
        parse_mode='HTML'
    )
    user_data[update.effective_user.id] = {"step": "awaiting_batch_links"}

# =====================================================
# /BATCH_SAME
# =====================================================
async def batch_same_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ <b>Access Denied</b>", parse_mode='HTML')
        return
    await update.message.reply_text(
        "🔗 Send first and last post links separated by dash (-)\n"
        "<b>Example:</b>\n<code>https://t.me/c/123/50 - https://t.me/c/123/55</code>",
        parse_mode='HTML'
    )
    user_data[update.effective_user.id] = {"step": "awaiting_batch_same_links"}

# =====================================================
# HELPER: Get keyboard for post (template-aware)
# =====================================================
async def get_keyboard_for_post(user_id: int, post_link: str = None, button_text: str = None, message_id: int = None) -> InlineKeyboardMarkup:
    """
    Smart keyboard generator:
    1. If button_text provided and not 'skip' -> parse it
    2. If template exists and post_link provided -> use template with link
    3. Fallback to cached buttons
    """
    # Priority 1: Direct button text provided
    if button_text and button_text.lower() != 'skip':
        # Try template parser first (for | separator)
        keyboard = parse_template_buttons(button_text, post_link)
        if keyboard:
            return keyboard
        # Fallback to legacy parser
        return parse_legacy_buttons(button_text)
    
    # Priority 2: User has template and post_link available
    template = get_template(user_id)
    if template and post_link:
        keyboard = parse_template_buttons(template, post_link)
        if keyboard:
            return keyboard
    
    # Priority 3: Cached buttons
    if message_id:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT button_data FROM message_buttons WHERE message_id = ?', (message_id,))
        result = c.fetchone()
        conn.close()
        if result:
            return parse_template_buttons(result[0], post_link) or parse_legacy_buttons(result[0])
    
    return None

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

    # ------------------- TEMPLATE SETTING -------------------
    if step == "awaiting_template":
        template_text = update.message.text
        save_template(user_id, template_text)
        
        # Show preview
        preview_markup = parse_template_buttons(template_text, "https://example.com")
        
        await update.message.reply_text(
            "✅ <b>Template Saved!</b>\n\n"
            f"<pre>{template_text}</pre>\n\n"
            "👇 <b>Preview:</b>",
            parse_mode='HTML',
            reply_markup=preview_markup
        )
        user_data[user_id] = {}
        return

    # ------------------- REP_BTN WITH TEMPLATE -------------------
    if step == "awaiting_post_link_for_template":
        post_link = update.message.text
        chat_id, message_id = extract_ids(post_link)
        
        if not chat_id or not message_id:
            await update.message.reply_text("❌ <b>Invalid link!</b>", parse_mode='HTML')
            return
        
        template = get_template(user_id)
        keyboard = parse_template_buttons(template, post_link)
        
        if not keyboard:
            await update.message.reply_text("❌ <b>No valid buttons generated from template!</b>", parse_mode='HTML')
            user_data[user_id] = {}
            return
        
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            
            # Cache buttons
            conn = get_db()
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO message_buttons (message_id, chat_id, button_data) 
                         VALUES (?, ?, ?)''', (message_id, chat_id, template))
            conn.commit()
            conn.close()
            
            await update.message.reply_text("✅ <b>Buttons updated with template!</b>", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode='HTML')
        
        user_data[user_id] = {}
        return

    # ------------------- BUTTON EDIT (LEGACY + TEMPLATE) -------------------
    if step == "awaiting_post_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_buttons"
        
        template = get_template(user_id)
        if template:
            await update.message.reply_text(
                "📝 <b>Send button layout or type 'template' to use your saved template:</b>\n\n"
                f"📋 Your template:\n<pre>{template}</pre>\n\n"
                "• Send custom buttons\n"
                "• Type <code>template</code> to use saved template\n"
                "• Type <code>skip</code> to keep current buttons",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "📝 Send button layout:\n"
                "<code>Label - URL</code>\n"
                "Double space = same row | Enter = new row\n"
                "Or type <code>skip</code> to cancel."
            )
        return

    if step == "awaiting_buttons":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)
        
        text_input = update.message.text
        
        if text_input.lower() == 'template':
            # Use saved template
            template = get_template(user_id)
            if not template:
                await update.message.reply_text("❌ <b>No template found!</b> Use /setbtns first.", parse_mode='HTML')
                return
            keyboard = parse_template_buttons(template, post_link)
        elif text_input.lower() == 'skip':
            await update.message.reply_text("⏭️ <b>Skipped.</b>", parse_mode='HTML')
            user_data[user_id] = {}
            return
        else:
            # Try template parser first, then legacy
            keyboard = parse_template_buttons(text_input, post_link)
            if not keyboard:
                keyboard = parse_legacy_buttons(text_input)
        
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            
            # Cache to DB
            if keyboard:
                conn = get_db()
                c = conn.cursor()
                c.execute('''INSERT OR REPLACE INTO message_buttons (message_id, chat_id, button_data) 
                             VALUES (?, ?, ?)''', (message_id, chat_id, text_input))
                conn.commit()
                conn.close()
            
            await update.message.reply_text("✅ <b>Buttons updated!</b>", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode='HTML')
        
        user_data[user_id] = {}
        return

    # ------------------- REPLACE -------------------
    if step == "awaiting_replace_link":
        user_data[user_id]["post_link"] = update.message.text
        user_data[user_id]["step"] = "awaiting_new_file"
        
        template = get_template(user_id)
        if template:
            await update.message.reply_text(
                "📎 <b>Send new content</b> (Photo/Video/Document/Animation/Audio/Sticker/Text) or type <code>skip</code>\n\n"
                f"📋 Template available: <code>/mybtns</code> to view",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("📎 Send new content or type <code>skip</code>", parse_mode='HTML')
        return

    if step == "awaiting_new_file":
        if update.message.text and update.message.text.lower() == "skip":
            user_data[user_id]["new_content"] = None
        else:
            user_data[user_id]["new_content"] = update.message
        
        user_data[user_id]["step"] = "awaiting_new_buttons"
        
        template = get_template(user_id)
        if template:
            await update.message.reply_text(
                "📝 <b>Send new button layout or type:</b>\n"
                "• <code>template</code> - Use saved template with post link\n"
                "• <code>skip</code> - Keep current buttons\n\n"
                f"📋 Template:\n<pre>{template}</pre>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "📝 Send new button layout or type <code>skip</code>\n"
                "Format: <code>Label - URL | Label2 - URL</code>",
                parse_mode='HTML'
            )
        return

    if step == "awaiting_new_buttons":
        post_link = user_data[user_id]["post_link"]
        chat_id, message_id = extract_ids(post_link)
        new_msg = user_data[user_id]["new_content"]
        text_input = update.message.text
        
        # Get keyboard
        if text_input.lower() == 'template':
            keyboard = await get_keyboard_for_post(user_id, post_link, None, message_id)
        elif text_input.lower() == 'skip':
            keyboard = await get_keyboard_for_post(user_id, None, None, message_id)
        else:
            keyboard = await get_keyboard_for_post(user_id, post_link, text_input, message_id)
        
        try:
            if new_msg:
                caption = new_msg.caption or new_msg.text or ""
                
                if new_msg.photo:
                    media = InputMediaPhoto(media=new_msg.photo[-1].file_id, caption=caption)
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=keyboard)
                elif new_msg.video:
                    media = InputMediaVideo(media=new_msg.video.file_id, caption=caption)
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=keyboard)
                elif new_msg.document:
                    media = InputMediaDocument(media=new_msg.document.file_id, caption=caption)
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=keyboard)
                elif new_msg.animation:
                    media = InputMediaAnimation(media=new_msg.animation.file_id, caption=caption)
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=keyboard)
                elif new_msg.audio:
                    media = InputMediaAudio(media=new_msg.audio.file_id, caption=caption)
                    await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=keyboard)
                elif new_msg.sticker:
                    await context.bot.send_sticker(chat_id=chat_id, sticker=new_msg.sticker.file_id)
                else:
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=caption, reply_markup=keyboard)
            else:
                if keyboard:
                    await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
            
            # Cache buttons
            if keyboard:
                conn = get_db()
                c = conn.cursor()
                c.execute('''INSERT OR REPLACE INTO message_buttons (message_id, chat_id, button_data) 
                             VALUES (?, ?, ?)''', (message_id, chat_id, text_input if text_input.lower() not in ['skip', 'template'] else get_template(user_id)))
                conn.commit()
                conn.close()
            
            await update.message.reply_text("✅ <b>Post replaced successfully!</b>", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode='HTML')
        
        user_data[user_id] = {}
        return

    # ------------------- BATCH DIFFERENT -------------------
    if step == "awaiting_batch_links":
        try:
            first_link, last_link = map(str.strip, update.message.text.split("-", 1))
        except:
            await update.message.reply_text("❌ <b>Invalid format!</b>\nSend like:\n<code>link1 - link2</code>", parse_mode='HTML')
            return
        
        first_chat, first_msg = extract_ids(first_link)
        last_chat, last_msg = extract_ids(last_link)
        
        if first_chat != last_chat:
            await update.message.reply_text("❌ <b>Messages must be from the same chat!</b>", parse_mode='HTML')
            return
        
        msg_ids = list(range(first_msg, last_msg + 1))
        user_data[user_id]["msg_ids"] = msg_ids
        user_data[user_id]["chat_id"] = first_chat
        user_data[user_id]["collected_contents"] = []
        user_data[user_id]["step"] = "awaiting_batch_contents"
        
        await update.message.reply_text(
            f"📎 Send content for <b>{len(msg_ids)}</b> messages one by one.\n"
            "Type <code>skip</code> to keep unchanged.",
            parse_mode='HTML'
        )
        return

    if step == "awaiting_batch_contents":
        msg_ids = user_data[user_id]["msg_ids"]
        collected = user_data[user_id].get("collected_contents", [])
        
        if update.message.text and update.message.text.lower() == "skip":
            collected.append(None)
        else:
            collected.append(update.message)
        
        user_data[user_id]["collected_contents"] = collected
        await update.message.reply_text(f"✅ Stored <b>{len(collected)}/{len(msg_ids)}</b>", parse_mode='HTML')
        
        if len(collected) >= len(msg_ids):
            user_data[user_id]["new_contents"] = collected
            user_data[user_id]["step"] = "awaiting_batch_buttons"
            
            template = get_template(user_id)
            if template:
                await update.message.reply_text(
                    "📝 Send button layout or type:\n"
                    "• <code>template</code> - Use template (auto-replaces {link})\n"
                    "• <code>skip</code> - Keep current buttons\n\n"
                    f"📋 Template:\n<pre>{template}</pre>",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text("📝 Send button layout or type <code>skip</code>", parse_mode='HTML')
        else:
            await update.message.reply_text("Send next message or type <code>skip</code>.", parse_mode='HTML')
        return

    # ------------------- BATCH SAME -------------------
    if step == "awaiting_batch_same_links":
        try:
            first_link, last_link = map(str.strip, update.message.text.split("-", 1))
        except:
            await update.message.reply_text("❌ <b>Invalid format!</b>\nSend like:\n<code>link1 - link2</code>", parse_mode='HTML')
            return
        
        first_chat, first_msg = extract_ids(first_link)
        last_chat, last_msg = extract_ids(last_link)
        
        if first_chat != last_chat:
            await update.message.reply_text("❌ <b>Messages must be from the same chat!</b>", parse_mode='HTML')
            return
        
        msg_ids = list(range(first_msg, last_msg + 1))
        user_data[user_id]["msg_ids"] = msg_ids
        user_data[user_id]["chat_id"] = first_chat
        user_data[user_id]["step"] = "awaiting_batch_same_content"
        
        await update.message.reply_text(
            f"📎 Send content for all <b>{len(msg_ids)}</b> messages or type <code>skip</code>",
            parse_mode='HTML'
        )
        return

    if step == "awaiting_batch_same_content":
        if update.message.text and update.message.text.lower() == "skip":
            user_data[user_id]["new_content"] = None
        else:
            user_data[user_id]["new_content"] = update.message
        
        user_data[user_id]["step"] = "awaiting_batch_same_buttons"
        
        template = get_template(user_id)
        if template:
            await update.message.reply_text(
                "📝 Send button layout or type:\n"
                "• <code>template</code> - Use template with each post link\n"
                "• <code>skip</code> - Keep current buttons\n\n"
                f"📋 Template:\n<pre>{template}</pre>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("📝 Send button layout or type <code>skip</code>", parse_mode='HTML')
        return

    # ------------------- APPLY BATCH & BATCH SAME -------------------
    if step in ["awaiting_batch_buttons", "awaiting_batch_same_buttons"]:
        errors = []
        text_input = update.message.text
        
        if step == "awaiting_batch_buttons":
            msg_ids = user_data[user_id]["msg_ids"]
            chat_id = user_data[user_id]["chat_id"]
            new_contents = user_data[user_id]["new_contents"]
            
            for idx, (mid, content) in enumerate(zip(msg_ids, new_contents)):
                # Generate post link for this message
                post_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{mid}"
                
                # Get keyboard
                if text_input.lower() == 'template':
                    keyboard = parse_template_buttons(get_template(user_id), post_link)
                elif text_input.lower() == 'skip':
                    keyboard = await get_keyboard_for_post(user_id, None, None, mid)
                else:
                    keyboard = parse_template_buttons(text_input, post_link) or parse_legacy_buttons(text_input)
                
                try:
                    if content:
                        caption = content.caption or content.text or ""
                        
                        if content.photo:
                            media = InputMediaPhoto(content.photo[-1].file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.video:
                            media = InputMediaVideo(content.video.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.document:
                            media = InputMediaDocument(content.document.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.animation:
                            media = InputMediaAnimation(content.animation.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.audio:
                            media = InputMediaAudio(content.audio.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.sticker:
                            await context.bot.send_sticker(chat_id=chat_id, sticker=content.sticker.file_id)
                        else:
                            await context.bot.edit_message_text(chat_id=chat_id, message_id=mid, text=caption, reply_markup=keyboard)
                    else:
                        if keyboard:
                            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup=keyboard)
                    
                    await asyncio.sleep(0.3)
                except Exception as e:
                    errors.append(f"❌ Message {mid}: {str(e)[:50]}")
            
            if errors:
                await update.message.reply_text("\n".join(errors), parse_mode='HTML')
            await update.message.reply_text("✅ <b>Batch replace completed!</b>", parse_mode='HTML')
            user_data[user_id] = {}
            return

        if step == "awaiting_batch_same_buttons":
            msg_ids = user_data[user_id]["msg_ids"]
            chat_id = user_data[user_id]["chat_id"]
            content = user_data[user_id]["new_content"]
            
            for mid in msg_ids:
                post_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{mid}"
                
                # Get keyboard
                if text_input.lower() == 'template':
                    keyboard = parse_template_buttons(get_template(user_id), post_link)
                elif text_input.lower() == 'skip':
                    keyboard = await get_keyboard_for_post(user_id, None, None, mid)
                else:
                    keyboard = parse_template_buttons(text_input, post_link) or parse_legacy_buttons(text_input)
                
                try:
                    if content:
                        caption = content.caption or content.text or ""
                        
                        if content.photo:
                            media = InputMediaPhoto(content.photo[-1].file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.video:
                            media = InputMediaVideo(content.video.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.document:
                            media = InputMediaDocument(content.document.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.animation:
                            media = InputMediaAnimation(content.animation.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.audio:
                            media = InputMediaAudio(content.audio.file_id, caption=caption)
                            await context.bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=keyboard)
                        elif content.sticker:
                            await context.bot.send_sticker(chat_id=chat_id, sticker=content.sticker.file_id)
                        else:
                            await context.bot.edit_message_text(chat_id=chat_id, message_id=mid, text=caption, reply_markup=keyboard)
                    else:
                        if keyboard:
                            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup=keyboard)
                    
                    await asyncio.sleep(0.3)
                except Exception as e:
                    errors.append(f"❌ Message {mid}: {str(e)[:50]}")
            
            if errors:
                await update.message.reply_text("\n".join(errors), parse_mode='HTML')
            await update.message.reply_text("✅ <b>Batch same content completed!</b>", parse_mode='HTML')
            user_data[user_id] = {}
            return

# =====================================================
# APPLICATION SETUP
# =====================================================
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Commands
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("setbtns", setbtns_cmd))
application.add_handler(CommandHandler("mybtns", mybtns_cmd))
application.add_handler(CommandHandler("delbtns", delbtns_cmd))
application.add_handler(CommandHandler("rep_btn", rep_btn))
application.add_handler(CommandHandler("replace", replace_cmd))
application.add_handler(CommandHandler("batch", batch_cmd))
application.add_handler(CommandHandler("batch_same", batch_same_cmd))

# Callback queries
application.add_handler(CallbackQueryHandler(callback_handler))

# Messages
application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))

# =====================================================
# RUN
# =====================================================
print("🤖 Bot is starting...")
application.run_polling()
