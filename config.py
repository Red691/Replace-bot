import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = list(map(int, os.environ.get("ADMIN_ID", "").split()))
