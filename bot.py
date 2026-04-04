from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN
from handlers.start import start
from handlers.edit_buttons import handle_buttons
from handlers.replace_post import handle_replace

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.ALL, handle_buttons))
    app.add_handler(MessageHandler(filters.ALL, handle_replace))

    app.run_polling()

if __name__ == "__main__":
    main()
