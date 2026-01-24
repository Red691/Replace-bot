import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Update

# Heroku Config Vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")  # optional
MAX_BUTTONS_PER_ROW = int(os.environ.get("MAX_BUTTONS_PER_ROW", 4))  # default 4
