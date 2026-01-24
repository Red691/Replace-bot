import os
from dotenv import load_dotenv

load_dotenv()  # load variables from .env

BOT_TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = os.environ.get("DEFAULT_CHANNEL_ID")
