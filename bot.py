import os
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserNotParticipant, ChatAdminRequired, UsernameNotOccupied, ChannelPrivate, PeerIdInvalid
from datetime import datetime, timedelta
import logging

from config import *
from database import Database
from user_client import UserClientManager
from utils import check_channel_membership, format_time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = Client(
    "ads_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize database
db = Database()

# Initialize user client manager
user_manager = UserClientManager(bot, db)

# Global force join state tracking
force_join_pending_users = set()

async def get_channel_join_link():
    """Get proper channel join link"""
    if str(FORCE_JOIN_CHANNEL).startswith("@"):
        return f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}"
    elif FORCE_JOIN_LINK:
        return FORCE_JOIN_LINK
    else:
        return f"https://t.me/{FORCE_JOIN_CHANNEL}"

async def is_user_member_of_channel(client, user_id, channel_id):
    """Enhanced channel membership check with better error handling"""
    try:
        # Try with bot client first
        chat_member = await client.get_chat_member(channel_id, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except (UserNotParticipant, PeerIdInvalid, UsernameNotOccupied):
        return False
    except Exception as e:
        logger.error(f"Error checking membership for user {user_id}: {e}")
        return False

async def force_join_check(client: Client, user_id: int, message: Message = None):
    """Comprehensive force join verification"""
    try:
        is_member = await is_user_member_of_channel(client, user_id, FORCE_JOIN_CHANNEL)
        
        if not is_member:
            join_link = await get_channel_join_link()
            channel_name = FORCE_JOIN_CHANNEL
            
            join_text = (
                "🔒 **Access Denied!**\n\n"
                "⚠️ **You must join our official channel first:**\n"
                f"**📢 {channel_name}**\n\n"
                "👉 **Steps to continue:**\n"
                "1. Click the button below to join\n"
                "2. Return here and send /start again\n\n"
                f"**⏰ Join timeout: {FORCE_JOIN_TIMEOUT_MINUTES} minutes**"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=join_link)],
                [InlineKeyboardButton("🔄 Check Again", callback_data=f"check_join_{user_id}")]
            ])
            
            force_join_pending_users.add(user_id)
            
            if message:
                await message.reply_text(join_text, reply_markup=keyboard, disable_web_page_preview=True)
            else:
                await client.send_message(user_id, join_text, reply_markup=keyboard, disable_web_page_preview=True)
            
            # Auto-remove from pending after timeout
            asyncio.create_task(auto_remove_pending_user(user_id))
            return False
        
        # User is member, remove from pending if exists
        force_join_pending_users.discard(user_id)
        return True
        
    except Exception as e:
        logger.error(f"Force join check error for {user_id}: {e}")
        return False

async def auto_remove_pending_user(user_id):
    """Remove user from pending list after timeout"""
    await asyncio.sleep(FORCE_JOIN_TIMEOUT_MINUTES * 60)
    force_join_pending_users.discard(user_id)

# Start command - FIXED FORCE JOIN
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"User_{user_id}"
    
    # Save user first
    db.add_user(user_id, username)
    
    # 🔒 FORCE JOIN CHECK - FIXED
    if not await force_join_check(client, user_id, message):
        return
    
    # User passed force join - show welcome
    user = db.get_user(user_id) or {}
    is_premium = user.get("is_premium", False) and user.get("subscription_expires", "") != ""
    
    welcome_text = (
        f"🤖 **Welcome back, {username}!**\n\n"
        f"👤 **ID:** `{user_id}`\n"
        f"📊 **Plan:** {'🌟 Premium' if is_premium else '🆓 Free'}\n\n"
        "**🚀 Quick Start:**\n"
        "1️⃣ `/login` - Link your account\n"
        "2️⃣ `/setad` - Create your ad\n"
        "3️⃣ `/addgroups` - Add target groups\n"
        "4️⃣ `/start_ads` - Go live!\n\n"
        "**📋 All Commands:**\n"
        "`/status` `/plans` `/help`"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Login Account", callback_data="start_login")],
        [InlineKeyboardButton("📢 My Status", callback_data="show_status")],
        [InlineKeyboardButton("💎 Upgrade", callback_data="view_plans")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")]
    ])
    
    await message.reply_text(welcome_text, reply_markup=keyboard, disable_web_page_preview=True)

# Help command
@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    await show_help_menu(client, message)

async def show_help_menu(client: Client, message_or_callback):
    help_text = """
📖 **Telegram Ads Bot - Commands**

**🔐 Account:**
• `/login` - Login your Telegram account
• `/status` - Check bot status
• `/logout` - Remove your session

**📢 Ads:**
• `/setad` - Set your advertisement
• `/viewad` - See current ad

**👥 Groups:**
• `/addgroups` - Add forwarding groups
• `/listgroups` - List all groups
• `/removegroup` - Remove a group

**⚙️ Control:**
• `/start_ads` - Start automation
• `/stop_ads` - Stop automation
• `/delay` - Set delay (Premium)

**💎 Premium:**
• `/plans` - View subscription plans
• `/upgrade` - Upgrade account
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_home")]
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(help_text, reply_markup=keyboard, disable_web_page_preview=True)
    else:
        await message_or_callback.edit_text(help_text, reply_markup=keyboard, disable_web_page_preview=True)

# Login command
@bot.on_message(filters.command("login") & filters.private)
async def login_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Force join check before login
    if not await force_join_check(client, user_id, message):
        return
    
    login_text = (
        "🔐 **Login Your Telegram Account**\n\n"
        "📱 **Enter your phone number:**\n"
        "`+1234567890`\n\n"
        "⚠️ **Security Notice:**\n"
        "• Session stored securely\n"
        "• Can logout anytime\n"
        "• Only your own account"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Cancel", callback_data="cancel_login")]
    ])
    
    await message.reply_text(login_text, reply_markup=keyboard)

# Status command
@bot.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Force join check
    if not await force_join_check(client, user_id, message):
        return
    
    await show_user_status(client, message, user_id)

async def show_user_status(client: Client, message_or_callback, user_id):
    user = db.get_user(user_id)
    
    if not user or not user.get('session_string'):
        status_text = "❌ **Not logged in**\n\nUse `/login` to start"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔐 Login", callback_data="start_login")]])
    else:
        groups = db.get_user_groups(user_id)
        ad = db.get_active_ad(user_id)
        
        is_premium = (user.get('is_premium', False) and 
                     user.get('subscription_expires', '') and 
                     datetime.fromisoformat(user['subscription_expires']) > datetime.now())
        
        status_parts = [
            f"👤 **User:** `{user_id}`",
            f"📱 **Phone:** `{user.get('phone_number', 'Not set')}`",
            f"⭐ **Plan:** {'🌟 Premium' if is_premium else '🆓 Free'}"
        ]
        
        status_parts.append("\n📢 **Advertisement:**")
        status_parts.append(f"• {'✅ Active' if ad else '❌ None'}")
        if ad:
            preview = ad.get('ad_text', '')[:60]
            status_parts.append(f"• `{preview}{'...' if len(ad.get('ad_text', '')) > 60 else ''}`")
        
        status_parts.append("\n👥 **Groups:**")
        status_parts.append(f"• **{len(groups)}** groups")
        
        status_parts.append("\n⚙️ **Automation:**")
        status_parts.append(f"• **Status:** {'🟢 Running' if user.get('is_active', False) else '🔴 Stopped'}")
        status_parts.append(f"• **Delay:** {user.get('delay_seconds', 300)}s")
        
        status_text = "\n".join(status_parts)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="show_status")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")]
        ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(status_text, reply_markup=keyboard, parse_mode='markdown')
    else:
        await message_or_callback.edit_text(status_text, reply_markup=keyboard, parse_mode='markdown')

# Plans command
@bot.on_message(filters.command("plans") & filters.private)
async def plans_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not await force_join_check(client, user_id, message):
        return
    
    plans_text = """
💎 **Premium Subscription Plans**

🆓 **FREE**
└─ 5min delay • Ads footer • Owner ads

💰 **BASIC** - ₹199/mo
├─ 10s delay • No footer
└─ No owner ads

🚀 **PRO** - ₹399/mo  
├─ All Basic + Analytics
└─ Priority support

⭐ **UNLIMITED** - ₹599/mo
└─ Everything + Custom features
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Upgrade", callback_data="upgrade_menu")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
    ])
    
    await message.reply_text(plans_text, reply_markup=keyboard)

# Generic command handler with force join
@bot.on_message(filters.command(["setad", "addgroups", "start_ads", "stop_ads", "delay"]) & filters.private)
async def protected_commands(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not await force_join_check(client, user_id, message):
        return
    
    # Forward to specific handlers
    cmd = message.command[0]
    if cmd == "setad":
        await setad_command(client, message)
    elif cmd == "addgroups":
        await message.reply_text("👥 **Add Groups**\n\nSend group usernames or links:\n`@groupname` or `t.me/groupname`")
    # Add other command handlers here...

@bot.on_message(filters.command("setad") & filters.private)
async def setad_command(client: Client, message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user or not user.get('session_string'):
        await message.reply_text("❌ **Login first:** `/login`")
        return
    
    await message.reply_text(
        "📢 **Set Advertisement**\n\n"
        "Send your ad (text/photo/video):\n\n"
        "**💡 Tips:**\n"
        "• Use emojis & formatting\n"
        "• Add your link/button\n"
        "• Max 4KB text\n\n"
        "`/cancel` to abort"
    )

# Callback query handler - FIXED
@bot.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    
    try:
        if data.startswith("check_join_"):
            # Force join verification
            if await force_join_check(client, user_id):
                await callback.message.delete()
                await start_command(client, callback.message)
            else:
                await callback.answer("❌ Still not joined!", show_alert=True)
            return
        
        elif data == "start_login":
            await callback.message.edit_text(
                "📱 **Enter Phone Number**\n\n"
                "`+1234567890`\n\n"
                "Send your number now:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="back_home")]
                ])
            )
            user_manager.login_states[user_id] = "awaiting_phone"
            
        elif data == "show_status":
            await show_user_status(client, callback, user_id)
            
        elif data == "show_help":
            await show_help_menu(client, callback)
            
        elif data == "view_plans":
            await plans_command(client, callback.message)
            
        elif data == "back_home":
            await callback.message.delete()
            await start_command(client, callback.message)
            
        else:
            await callback.answer("Feature coming soon!")
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback.answer("Error occurred, try /start", show_alert=True)
    
    await callback.answer()

# Message handler for login flow and other states
@bot.on_message(filters.private & ~filters.command("start"))
async def message_handler(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Skip force join check for login flow messages
    if user_id in user_manager.login_states:
        await user_manager.handle_login_flow(message)
        return
    
    # Force join check for other messages
    if user_id in force_join_pending_users:
        await force_join_check(client, user_id, message)
        return

# Admin commands (Owner only)
@bot.on_message(filters.command(["stats", "broadcast"]) & filters.private & filters.user(OWNER_ID))
async def admin_commands(client: Client, message: Message):
    if message.command[0] == "stats":
        active_users = len(db.get_active_users())
        stats_text = f"📊 **Stats**\n\n👥 Active users: `{active_users}`\n🤖 Sessions: `{len(user_manager.active_sessions)}`"
        await message.reply_text(stats_text)

# Main function
async def main():
    logger.info("🤖 Starting Telegram Ads Bot...")
    
    # Create directories
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    await bot.start()
    logger.info("✅ Bot started!")
    
    # Start user manager
    await user_manager.start()
    logger.info("✅ User manager ready!")
    
    logger.info("🚀 Bot fully operational!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())