"""
🚀 Advanced Command Handlers - Fixed Architecture
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait

from utils import safe_int, sanitize_input, rate_limit_check, AntiFlood
from database import DatabaseConnection

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsStats:
    total_forwards: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0
    top_groups: List[Dict] = None


class AdvancedCommandHandlers:
    def __init__(self, bot: Client, db: DatabaseConnection, user_manager: Any):
        self.bot = bot
        self.db = db
        self.user_manager = user_manager
        self.rate_limiter = AntiFlood(max_requests=5, window=60)
        self.cooldowns: Dict[int, Dict[str, float]] = {}
        logger.info("✅ Advanced handlers ready")

    async def _check_user_access(self, user_id: int, command: str) -> bool:
        if not await rate_limit_check(self.rate_limiter, user_id):
            return False
        now = datetime.now().timestamp()
        last = self.cooldowns.get(user_id, {}).get(command, 0)
        if now - last < 2:
            return False
        self.cooldowns.setdefault(user_id, {})[command] = now
        return True

    # ================= ANALYTICS =================
    async def analytics_command(self, client: Client, message: Message):
        if not await self._check_user_access(message.from_user.id, "analytics"):
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Today", callback_data="analytics_1d"),
             InlineKeyboardButton("📈 Week", callback_data="analytics_7d")],
            [InlineKeyboardButton("📊 Month", callback_data="analytics_30d"),
             InlineKeyboardButton("🌐 All Time", callback_data="analytics_all")]
        ])

        await message.reply_text(
            "📊 **Analytics Dashboard**\nSelect period:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    # ================= MY ADS =================
    async def myads_command(self, client: Client, message: Message):
        if not await self._check_user_access(message.from_user.id, "myads"):
            return

        user_id = message.from_user.id
        ads = []

        try:
            with self.db.db.get_connection() as conn:
                ads = conn.execute(
                    "SELECT id, ad_text, is_active FROM ads WHERE user_id=?",
                    (user_id,)
                ).fetchall()
        except Exception as e:
            logger.error(e)

        if not ads:
            await message.reply_text("❌ No ads found. Use /setad")
            return

        text = "📢 **Your Ads**\n\n"
        for ad in ads:
            status = "🟢 Active" if ad["is_active"] else "🔴 Off"
            preview = sanitize_input(ad["ad_text"])[:40]
            text += f"`{ad['id']}` {status}\n`{preview}`\n\n"

        await message.reply_text(text, parse_mode="Markdown")

    # ================= HEALTH =================
    async def checkhealth_command(self, client: Client, message: Message):
        user_id = message.from_user.id
        session = self.user_manager.active_sessions.get(user_id)

        if not session:
            await message.reply_text("❌ No active session. Use /login")
            return

        await message.reply_text("🔍 Checking health...")
        issues = []

        try:
            await session.get_me()
        except FloodWait as e:
            issues.append(f"Flood wait: {e.value}s")
        except Exception as e:
            issues.append(str(e)[:50])

        if issues:
            await message.reply_text("⚠️ Issues:\n" + "\n".join(issues))
        else:
            await message.reply_text("✅ Session healthy")

    # ================= CALLBACKS =================
    async def callback_handler(self, client: Client, callback: CallbackQuery):
        data = callback.data
        user_id = callback.from_user.id

        if not await self._check_user_access(user_id, f"cb_{data}"):
            await callback.answer("Wait...", show_alert=False)
            return

        if data.startswith("analytics_"):
            await callback.edit_message_text("📊 Analytics loading...")

        await callback.answer()


# =====================================================
# REGISTER FUNCTION (THIS FIXES YOUR ORIGINAL CRASH)
# =====================================================
def register_advanced_handlers(app: Client, db: DatabaseConnection, user_manager: Any):
    h = AdvancedCommandHandlers(app, db, user_manager)

    app.add_handler(filters.command("analytics") & filters.private, h.analytics_command)
    app.add_handler(filters.command("myads") & filters.private, h.myads_command)
    app.add_handler(filters.command("health") & filters.private, h.checkhealth_command)
    app.add_handler(filters.callback_query(), h.callback_handler)

    logger.info("✅ Advanced handlers registered")
    return h