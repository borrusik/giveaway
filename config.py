import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///invite2win.db")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))