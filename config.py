import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# Channel settings
CHANNEL_ID = os.getenv("CHANNEL_ID")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set")

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip('@')
if not CHANNEL_USERNAME:
    raise ValueError("CHANNEL_USERNAME environment variable is not set")

# Bot username
BOT_USERNAME = os.getenv("BOT_USERNAME", "AirChainMiniAppBot").strip('@')

# Admin settings
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = list(map(int, admin_ids_str.split(",")))
    except ValueError:
        raise ValueError("ADMIN_IDS must be comma-separated integers")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///invite2win.db")

# Logging settings
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())

# Draw settings
DEFAULT_DRAW_DURATION = int(os.getenv("DEFAULT_DRAW_DURATION", "7"))  # 7 days by default
SCHEDULER_CHECK_INTERVAL = int(os.getenv("SCHEDULER_CHECK_INTERVAL", "3600"))  # 1 hour by default
REFERRAL_TICKETS = int(os.getenv("REFERRAL_TICKETS", "1"))  # Tickets per referral

# Rate limiting
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "5"))  # Messages per minute