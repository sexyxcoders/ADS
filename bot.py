"""
🚀 Telegram Ads Bot - Production Main (2026 Edition)
Fully async, production-hardened, enterprise-grade
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserNotParticipant, ChatAdminRequired

# Local imports - ALL ASYNC
from config import *
from database import AsyncDatabase  # ✅ Async DB
from user_client import UserClientManager  # ✅ Async manager
from admin_handlers import register_admin_handlers  # ✅ Async admin
from utils import format_time, AntiFlood, sanitize_input, safe_int  # ✅ Utils
from advanced_features import init_advanced_features  # ✅ Analytics/Health

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdsBot:
    """🎯 Main Bot Orchestrator - Production Ready"""
    
    def __init__(self):
        self.bot = Client(
            "ads_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=8,  # ✅ Optimized workers
            timeout=30   # ✅ Request timeout
        )
        
        # Core dependencies
        self.db = AsyncDatabase()
        self.user_manager = UserClientManager(self.bot, self.db)
        
        # Security & state
        self.global_flood = AntiFlood(max_requests=10, window=timedelta(minutes=1))
        self.user_states: Dict[int, str] = {}  # user_id → state
        
        # Admin
        register_admin_handlers(self.bot, self.db, self.user_manager, OWNER_ID)
        
        # Advanced features
        self.advanced_features = init_advanced_features(self.bot, self.db)
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all core handlers"""
        self.bot.add_handler(filters.command("start") & filters.private, self.start_command)
        self.bot.add_handler(filters.command("help") & filters.private, self.help_command)
        self.bot.add_handler(filters.command("login") & filters.private, self.login_command)
        self.bot.add_handler(filters.command("status") & filters.private, self.status_command)
        self.bot.add_handler(filters.command("setad") & filters.private, self.setad_command)
        self.bot.add_handler(filters.command("plans") & filters.private, self.plans_command)
        self.bot.add_handler(filters.command("cancel") & filters.private, self.cancel_command)
        
        # Message states & callbacks
        self.bot.add_handler(filters.private & ~filters.command(list("starthlp")), self.message_handler)
        self.bot.add_handler(filters.callback_query(), self.callback_handler)
    
    async def start_command(self, client: Client, message: Message):
        """🚀 Welcome - Async + Premium Check"""
        user_id = message.from_user.id
        username = message.from_user.username or "User"
        
        # Rate limit
        if not await self.global_flood.check(user_id):
            await message.reply_text("⏳ **Rate Limited** - Try again in 1 minute")
            return
        
        # Add/track user async
        await self.db.add_user(user_id, username)
        user = await self.db.get_user(user_id)
        
        is_premium = user.get('is_premium', False) and user.get('premium_expires') and \
                    datetime.fromisoformat(user['premium_expires']) > datetime.now()
        
        welcome_text = f"""
🤖 **Welcome to Telegram Ads Forwarding BOT!**

👤 **{username}**
📊 **Status:** {'🌟 Premium' if is_premium else '🆓 Free'}

**🔹 Features:**
✅ Auto-forward ads to groups
✅ Campaign management  
✅ Real-time analytics
✅ Mention notifications

**📋 Commands:**
`/login` - Connect account
`/setad` - Set advertisement  
`/addgroups` - Add groups
`/start_ads` - Start automation
`/status` - Bot status
`/plans` - Premium plans

**🎯 Quick Start:**
1️⃣ `/login` → 2️⃣ `/setad` → 3️⃣ `/addgroups` → 4️⃣ `/start_ads`
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 Login Now", callback_data="start_login")],
            [InlineKeyboardButton("💎 Premium Plans", callback_data="view_plans")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        
        await message.reply_text(welcome_text, reply_markup=keyboard)
        logger.info(f"User {user_id} (@{username}) started bot")
    
    async def help_command(self, client: Client, message: Message):
        """📖 Help - Comprehensive"""
        help_text = """
📖 **Telegram Ads Bot Guide**

**🔐 Account:**
`/login` - Login session
`/logout` - Remove session

**📢 Ads:**
`/setad` - Set ad (text/media)
`/viewad` - Current ad

**👥 Groups:**
`/addgroups` - Add forwarding groups
`/listgroups` - View groups
`/removegroup <id>` - Remove group

**⚙️ Automation:**
`/start_ads` - Start forwarding
`/stop_ads` - Stop forwarding
`/status` - Status + stats

**💎 Premium:**
`/plans` - View plans
`/delay` - Custom delay (Premium)

**👨‍💼 Admin (Owner):**
`/payments` - Payment dashboard
`/approve/reject` - Process payments
`/stats` - Bot analytics
`/ownerads` - Promo ads
`/broadcast` - Mass broadcast
        """
        await message.reply_text(help_text)
    
    async def login_command(self, client: Client, message: Message):
        """🔐 Login Flow"""
        user_id = message.from_user.id
        
        await message.reply_text(
            "🔐 **Login Your Telegram Account**\n\n"
            "**⚠️ Secure notes:**\n"
            "• Sessions encrypted\n"
            "• No message access\n"
            "• `/logout` anytime\n\n"
            "**📱 Process:**\n"
            "1. Phone (+country code)\n"
            "2. OTP code\n"
            "3. 2FA (if enabled)\n\n"
            "**👇 Click to start:**"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Start Login", callback_data="start_login")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_login")]
        ])
        await message.reply_text("Ready?", reply_markup=keyboard)
    
    async def status_command(self, client: Client, message: Message):
        """📊 Real-time Status"""
        user_id = message.from_user.id
        user = await self.db.get_user(user_id)
        
        if not user or not user.get('session_string'):
            await message.reply_text("❌ **Login first:** `/login`")
            return
        
        # Parallel data fetch
        groups_task = self.db.get_user_groups(user_id)
        ad_task = self.db.get_active_ad(user_id)
        groups, ad = await asyncio.gather(groups_task, ad_task)
        
        is_premium = (user.get('is_premium') and 
                     user.get('premium_expires') and 
                     datetime.fromisoformat(user['premium_expires']) > datetime.now())
        
        status_text = f"""
📊 **Status** `{datetime.now().strftime('%H:%M')} UTC`

👤 **Account:**
`{user_id}` | {user.get('phone_number', 'Not set')}
Tier: {'🌟 Premium' if is_premium else '🆓 Free'}

📢 **Ad:** {'✅ Active' if ad else '❌ None'}
👥 **Groups:** {len(groups)}
⚙️ **Automation:** {'🟢 Running' if user.get('is_active') else '🔴 Stopped'}
⏱️ **Delay:** {user.get('delay_seconds', 300)}s

📈 **Premium:** {'✅ Active' if is_premium else '💎 /plans'}
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="user_settings")]
        ])
        
        await message.reply_text(status_text, reply_markup=keyboard)
    
    async def setad_command(self, client: Client, message: Message):
        """📢 Ad Setup"""
        user_id = message.from_user.id
        user = await self.db.get_user(user_id)
        
        if not user or not user.get('session_string'):
            await message.reply_text("❌ **Login first:** `/login`")
            return
        
        self.user_states[user_id] = "awaiting_ad"
        await message.reply_text(
            "📢 **Set Advertisement**\n\n"
            "✅ **Send your ad:**\n"
            "• Text message\n"
            "• Photo + caption\n"
            "• Video + caption\n\n"
            "`/cancel` to abort"
        )
    
    async def plans_command(self, client: Client, message: Message):
        """💎 Premium Plans"""
        plans_text = """
💎 **Premium Plans** (No owner ads!)

**🆓 Free:**
• 5min delay min
• Owner promo ads
• Bio/name locked

**💰 Basic** ₹199/mo:
✅ **10s delay**
✅ **No owner ads**
✅ **Free bio/name**

**🚀 Pro** ₹399/mo:
✅ **All Basic**
✅ **Analytics**
✅ **Priority support**

**⭐ Unlimited** ₹599/mo:
✅ **All Pro**
✅ **Fastest speed**
✅ **Custom features**

**💳 Upgrade:** `/upgrade <plan>`
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade", callback_data="upgrade_premium")],
            [InlineKeyboardButton("🔙 Main", callback_data="back_home")]
        ])
        await message.reply_text(plans_text, reply_markup=keyboard)
    
    async def cancel_command(self, client: Client, message: Message):
        """❌ Cancel State"""
        user_id = message.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
            await message.reply_text("✅ **Cancelled**")
        else:
            await message.reply_text("ℹ️ **No active operation**")
    
    async def callback_handler(self, client: Client, callback: CallbackQuery):
        """🎛️ Smart Callbacks"""
        data = callback.data
        user_id = callback.from_user.id
        
        try:
            if data == "start_login":
                await callback.message.edit_text(
                    "📱 **Enter Phone**\n\n"
                    "`+1234567890` format\n\n"
                    "`/cancel` to stop"
                )
                self.user_states[user_id] = "awaiting_phone"
                
            elif data == "view_plans":
                await self.plans_command(client, callback.message)
                
            elif data == "help":
                await self.help_command(client, callback.message)
                
            elif data == "upgrade_premium":
                await callback.message.edit_text(
                    "💎 **Choose Plan:**\n\n"
                    "`/upgrade basic` | `pro` | `unlimited`"
                )
                
            elif data == "refresh_status":
                await self.status_command(client, callback.message)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Callback error {user_id}: {e}")
            await callback.answer("❌ Error occurred")
    
    async def message_handler(self, client: Client, message: Message):
        """📨 Universal Message Handler"""
        user_id = message.from_user.id
        
        # State machine
        if user_id in self.user_states:
            state = self.user_states[user_id]
            
            if state == "awaiting_phone":
                await self.user_manager.handle_phone(message)
            elif state == "awaiting_ad":
                await self.user_manager.handle_ad_submission(message)
            elif state == "awaiting_otp":
                await self.user_manager.handle_otp(message)
            
            return
        
        # Fallback
        await message.reply_text("❓ **Use:** `/help`")
    
    async def start(self):
        """🎬 Production Startup"""
        logger.info("🤖 Starting Ads Bot...")
        
        # Ensure directories
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        
        # Graceful startup
        try:
            await self.bot.start()
            logger.info("✅ Bot online!")
            
            # Init subsystems
            await self.db.init()
            await self.user_manager.start()
            await self.advanced_features.start()
            
            # Health check
            await self.advanced_features.health_check()
            
            # Keep alive
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("🛑 Graceful shutdown...")
        except Exception as e:
            logger.error(f"💥 Fatal: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """🔄 Graceful Shutdown"""
        logger.info("🔄 Shutting down...")
        
        await self.user_manager.stop()
        await self.db.close()
        await self.advanced_features.stop()
        await self.bot.stop()
        
        logger.info("✅ Shutdown complete")

async def main():
    """🚀 Entry Point"""
    bot = AdsBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())