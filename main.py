#!/usr/bin/env python3
"""
🚀 Telegram Ads Forwarding BOT — Production Async Edition
Integrated Handlers + Enterprise Structure
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from database import Database
from user_client import UserClientManager
from handlers import AdHandler, GroupHandler, AutomationHandler, DelayHandler, UpgradeHandler
from admin_handlers import AdminHandler
from advanced_handlers import AdvancedCommandHandlers
from utils import AntiFlood

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger("AdsBot")

# ================= CORE BOT CLASS =================
class AdsBot:
    def __init__(self):
        self.bot = Client(
            "ads_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=8
        )

        # Core systems
        self.db = Database()
        self.user_manager = UserClientManager(self.bot, self.db)

        # Handlers
        self.ad_handler = AdHandler(self.bot, self.db, self.user_manager)
        self.group_handler = GroupHandler(self.bot, self.db, self.user_manager)
        self.automation_handler = AutomationHandler(self.bot, self.db, self.user_manager)
        self.delay_handler = DelayHandler(self.bot, self.db)
        self.upgrade_handler = UpgradeHandler(self.bot, self.db)
        self.admin_handler = AdminHandler(self.bot, self.db, self.user_manager, OWNER_ID)
        self.advanced_handlers = AdvancedCommandHandlers(self.bot, self.db, self.user_manager)

        # Protection
        self.flood = AntiFlood(max_requests=10, window=timedelta(minutes=1))

        self.register_handlers()

    # ================= COMMANDS =================

    def register_handlers(self):

        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_command(client: Client, message: Message):
            user_id = message.from_user.id
            username = message.from_user.username or "User"

            if not await self.flood.check(user_id):
                await message.reply_text("⏳ Too many requests. Try again later.")
                return

            self.db.add_user(user_id, username)
            user = self.db.get_user(user_id)

            is_premium = user and user['is_premium']

            text = f"""
🤖 **Welcome to Ads Forwarding Bot**

👤 {username}
📊 Status: {'🌟 Premium' if is_premium else '🆓 Free'}

**Quick Start**
/login → /setad → /addgroups → /start_ads
"""
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Login", callback_data="login_now")],
                [InlineKeyboardButton("💎 Plans", callback_data="show_plans")]
            ])

            await message.reply_text(text, reply_markup=kb)

        # Register existing handlers
        self.bot.add_handler(filters.command("setad") & filters.private, self.ad_handler.start_ad_setup)
        self.bot.add_handler(filters.command("addgroups") & filters.private, self.group_handler.add_groups_command)
        self.bot.add_handler(filters.command("start_ads") & filters.private, self.automation_handler.start_ads_command)
        self.bot.add_handler(filters.command("stop_ads") & filters.private, self.automation_handler.stop_ads_command)
        self.bot.add_handler(filters.command("delay") & filters.private, self.delay_handler.delay_command)
        self.bot.add_handler(filters.command("upgrade") & filters.private, self.upgrade_handler.upgrade_command)

    # ================= STARTUP =================

    async def start(self):
        logger.info("🚀 Starting Ads Bot...")
        os.makedirs(SESSIONS_DIR, exist_ok=True)

        await self.bot.start()
        me = await self.bot.get_me()
        logger.info(f"✅ Bot Online: @{me.username}")

        await self.user_manager.start()

        logger.info("🎉 SYSTEM READY")
        await asyncio.Event().wait()

# ================= ENTRY =================
async def main():
    bot = AdsBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())#!/usr/bin/env python3
"""
🚀 Telegram Ads Forwarding BOT — Production Async Edition
Integrated Handlers + Enterprise Structure
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from database import Database
from user_client import UserClientManager
from handlers import AdHandler, GroupHandler, AutomationHandler, DelayHandler, UpgradeHandler
from admin_handlers import AdminHandler
from advanced_handlers import AdvancedCommandHandlers
from utils import AntiFlood

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger("AdsBot")

# ================= CORE BOT CLASS =================
class AdsBot:
    def __init__(self):
        self.bot = Client(
            "ads_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=8
        )

        # Core systems
        self.db = Database()
        self.user_manager = UserClientManager(self.bot, self.db)

        # Handlers
        self.ad_handler = AdHandler(self.bot, self.db, self.user_manager)
        self.group_handler = GroupHandler(self.bot, self.db, self.user_manager)
        self.automation_handler = AutomationHandler(self.bot, self.db, self.user_manager)
        self.delay_handler = DelayHandler(self.bot, self.db)
        self.upgrade_handler = UpgradeHandler(self.bot, self.db)
        self.admin_handler = AdminHandler(self.bot, self.db, self.user_manager, OWNER_ID)
        self.advanced_handlers = AdvancedCommandHandlers(self.bot, self.db, self.user_manager)

        # Protection
        self.flood = AntiFlood(max_requests=10, window=timedelta(minutes=1))

        self.register_handlers()

    # ================= COMMANDS =================

    def register_handlers(self):

        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_command(client: Client, message: Message):
            user_id = message.from_user.id
            username = message.from_user.username or "User"

            if not await self.flood.check(user_id):
                await message.reply_text("⏳ Too many requests. Try again later.")
                return

            self.db.add_user(user_id, username)
            user = self.db.get_user(user_id)

            is_premium = user and user['is_premium']

            text = f"""
🤖 **Welcome to Ads Forwarding Bot**

👤 {username}
📊 Status: {'🌟 Premium' if is_premium else '🆓 Free'}

**Quick Start**
/login → /setad → /addgroups → /start_ads
"""
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Login", callback_data="login_now")],
                [InlineKeyboardButton("💎 Plans", callback_data="show_plans")]
            ])

            await message.reply_text(text, reply_markup=kb)

        # Register existing handlers
        self.bot.add_handler(filters.command("setad") & filters.private, self.ad_handler.start_ad_setup)
        self.bot.add_handler(filters.command("addgroups") & filters.private, self.group_handler.add_groups_command)
        self.bot.add_handler(filters.command("start_ads") & filters.private, self.automation_handler.start_ads_command)
        self.bot.add_handler(filters.command("stop_ads") & filters.private, self.automation_handler.stop_ads_command)
        self.bot.add_handler(filters.command("delay") & filters.private, self.delay_handler.delay_command)
        self.bot.add_handler(filters.command("upgrade") & filters.private, self.upgrade_handler.upgrade_command)

    # ================= STARTUP =================

    async def start(self):
        logger.info("🚀 Starting Ads Bot...")
        os.makedirs(SESSIONS_DIR, exist_ok=True)

        await self.bot.start()
        me = await self.bot.get_me()
        logger.info(f"✅ Bot Online: @{me.username}")

        await self.user_manager.start()

        logger.info("🎉 SYSTEM READY")
        await asyncio.Event().wait()

# ================= ENTRY =================
async def main():
    bot = AdsBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())