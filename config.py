import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Update

# Heroku Config Vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
