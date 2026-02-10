import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8525366225:AAG_nUH9HfmDz8TpBxg-gt2pMDesnfY71L4")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_database.db")

# Admin Configuration
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@TechyNetwork")

# Bot Username (without @)
BOT_USERNAME = os.getenv("BOT_USERNAME", "kidoramusicbot")

# Tier Configuration
FREE_TIER = {
    "min_delay": 300,  # 5 minutes in seconds
    "bio_lock": True,
    "name_lock": True,
    "forced_footer": f"\n\nPowered by @{BOT_USERNAME} | Upgrade for fast ads 🚀",
    "owner_ads_enabled": True,
}

PAID_TIER = {
    "min_delay": 10,  # 10 seconds
    "max_delay": 600,  # 10 minutes
    "bio_lock": False,
    "name_lock": False,
    "forced_footer": "",
    "owner_ads_enabled": False,
}

# Pricing Plans
PRICING = {
    "basic": {"price": 199, "duration_days": 30, "name": "Basic Plan"},
    "pro": {"price": 399, "duration_days": 30, "name": "Pro Plan"},
    "unlimited": {"price": 599, "duration_days": 30, "name": "Unlimited Plan"},
}

# Session Storage
SESSIONS_DIR = "sessions"
