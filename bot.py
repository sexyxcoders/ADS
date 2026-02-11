import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserNotParticipant, ChatAdminRequired
from datetime import datetime, timedelta
import logging

from config import *
from database import Database
from user_client import UserClientManager
from utils import format_time

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

# Start command
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Add user to database
    db.add_user(user_id, username)

    user = db.get_user(user_id)

    welcome_text = f"""
🤖 **Welcome to Telegram Ads Forwarding BOT!**

👤 User: {username or 'User'}
📊 Status: {'🌟 Premium' if user and user['is_premium'] else '🆓 Free'}

**🔹 What I can do:**
✅ Forward your ads to multiple groups automatically
✅ Manage your ad campaigns
✅ Track forwarding logs
✅ Notify you when mentioned in groups

**📋 Available Commands:**
/login - Login with your Telegram account
/setad - Set your advertisement
/addgroups - Add groups for forwarding
/start_ads - Start forwarding automation
/stop_ads - Stop forwarding automation
/status - Check your bot status
/delay - Set forwarding delay (Premium only)
/plans - View premium plans
/help - Get help

**🎯 Get Started:**
1. Use /login to connect your account
2. Use /setad to set your advertisement
3. Use /addgroups to add groups
4. Use /start_ads to begin automation!
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Login Now", callback_data="start_login")],
        [InlineKeyboardButton("💎 View Plans", callback_data="view_plans")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])

    await message.reply_text(welcome_text, reply_markup=keyboard)

# Help command
@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    help_text = """
📖 **Bot Commands Guide**

**🔐 Account Management:**
/login - Login with your Telegram account session
/logout - Logout and remove your session

**📢 Ad Management:**
/setad - Set/update your advertisement (text or media)
/viewad - View your current advertisement

**👥 Group Management:**
/addgroups - Add groups for ad forwarding
/listgroups - View all your groups
/removegroup - Remove a group

**⚙️ Automation:**
/start_ads - Start automatic forwarding
/stop_ads - Stop automatic forwarding
/status - Check bot status and statistics

**💎 Premium Features:**
/delay - Set custom forwarding delay (10s - 10min)
/plans - View available premium plans
/upgrade - Upgrade to premium

**👨‍💼 Admin Commands (Owner only):**
/ownerads - Manage promotional ads
/broadcast - Broadcast owner ads to free users
/payments - View pending payment requests
/approve - Approve payment request
/stats - View bot statistics

**🔔 Features:**
• Auto log channel for forwarding reports
• Mention notifications in groups
• Bio/Name lock (Free tier)
• Custom delays (Premium)
    """
    await message.reply_text(help_text)

# Login command
@bot.on_message(filters.command("login") & filters.private)
async def login_command(client: Client, message: Message):
    user_id = message.from_user.id

    login_text = """
🔐 **Login to Your Telegram Account**

To use this bot, you need to login with your Telegram account session.

**⚠️ Important Notes:**
• Your session is stored securely
• We never access your messages or contacts
• You can logout anytime with /logout
• Use only your own account

**📱 How to login:**
1. Click "Start Login" below
2. Enter your phone number (with country code)
3. Enter the OTP code you receive
4. Enter 2FA password if you have one

**Ready to login?**
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Start Login", callback_data="start_login")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_login")]
    ])

    await message.reply_text(login_text, reply_markup=keyboard)

# Status command
@bot.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user or not user['session_string']:
        await message.reply_text("❌ You haven't logged in yet. Use /login to get started.")
        return

    groups = db.get_user_groups(user_id)
    ad = db.get_active_ad(user_id)

    is_premium = user['is_premium'] and user['subscription_expires'] and \
                 datetime.fromisoformat(user['subscription_expires']) > datetime.now()

    status_text = f"""
📊 **Your Bot Status**

👤 **Account Info:**
• User ID: `{user_id}`
• Phone: `{user['phone_number'] or 'Not set'}`
• Tier: {'🌟 Premium' if is_premium else '🆓 Free'}

📢 **Advertisement:**
• Status: {'✅ Set' if ad else '❌ Not set'}
{'• Ad Text: ' + (ad['ad_text'][:50] + '...' if len(ad['ad_text']) > 50 else ad['ad_text']) if ad else ''}

👥 **Groups:**
• Total Groups: {len(groups)}
• Groups: {', '.join([g['group_name'] for g in groups[:5]]) if groups else 'None'}

⚙️ **Automation:**
• Status: {'🟢 Active' if user['is_active'] else '🔴 Stopped'}
• Delay: {user['delay_seconds']} seconds
• Log Channel: {'✅ Created' if user['log_channel_id'] else '⏳ Pending'}

📈 **Subscription:**
"""

    if is_premium:
        expires = datetime.fromisoformat(user['subscription_expires'])
        days_left = (expires - datetime.now()).days
        status_text += f"• Expires: {expires.strftime('%Y-%m-%d')}\n"
        status_text += f"• Days Left: {days_left} days\n"
    else:
        status_text += "• Type: Free tier\n"
        status_text += "• Min Delay: 5 minutes\n"
        status_text += "• Upgrade: /plans\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ])

    await message.reply_text(status_text, reply_markup=keyboard)

# Set ad command
@bot.on_message(filters.command("setad") & filters.private)
async def setad_command(client: Client, message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user or not user['session_string']:
        await message.reply_text("❌ You haven't logged in yet. Use /login first.")
        return

    await message.reply_text(
        "📢 **Set Your Advertisement**\n\n"
        "Please send me your advertisement message. You can send:\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n\n"
        "This will be forwarded to all your groups.\n\n"
        "Send /cancel to cancel."
    )

# Plans command
@bot.on_message(filters.command("plans") & filters.private)
async def plans_command(client: Client, message: Message):
    plans_text = """
💎 **Premium Plans**

**🆓 Free Plan:**
• Unlimited groups
• 5 minutes minimum delay
• Forced footer on ads
• Owner promotional ads
• Bio/Name locked to bot

**💰 Basic Plan - ₹199/month:**
• Unlimited groups
• 10 seconds minimum delay
• No forced footer
• No owner ads
• Free bio/name

**🚀 Pro Plan - ₹399/month:**
• All Basic features
• Priority support
• Advanced analytics
• Custom features

**⭐ Unlimited Plan - ₹599/month:**
• All Pro features
• Fastest forwarding
• Dedicated support
• Early access to new features

**💳 How to upgrade:**
Use /upgrade to start the payment process.
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade Now", callback_data="upgrade_premium")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
    ])

    await message.reply_text(plans_text, reply_markup=keyboard)

# Admin: Owner ads
@bot.on_message(filters.command("ownerads") & filters.private & filters.user(OWNER_ID))
async def owner_ads_command(client: Client, message: Message):
    await message.reply_text(
        "📢 **Manage Owner Promotional Ads**\n\n"
        "Send me the advertisement you want to save.\n"
        "This ad will be used for promotional purposes on free user accounts.\n\n"
        "Send /cancel to cancel."
    )

# Admin: Broadcast owner ads
@bot.on_message(filters.command("broadcast") & filters.private & filters.user(OWNER_ID))
async def broadcast_command(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("Usage: /broadcast <ad_id>")
        return

    try:
        ad_id = int(args[1])
    except:
        await message.reply_text("❌ Invalid ad ID")
        return

    await message.reply_text(f"🚀 Starting broadcast of owner ad #{ad_id} to free users...")

    # This will trigger owner ads through free user accounts
    await user_manager.broadcast_owner_ad(ad_id)

    await message.reply_text("✅ Broadcast completed!")

# Admin: View stats
@bot.on_message(filters.command("stats") & filters.private & filters.user(OWNER_ID))
async def stats_command(client: Client, message: Message):
    active_users = db.get_active_users()
    free_users = db.get_free_users()

    stats_text = f"""
📊 **Bot Statistics**

👥 **Users:**
• Total Active: {len(active_users)}
• Free Users: {len(free_users)}
• Premium Users: {len(active_users) - len(free_users)}

⚙️ **System:**
• Running Sessions: {len(user_manager.active_sessions)}
• Database: Connected
• Bot: Online

📈 **Activity:**
• Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """

    await message.reply_text(stats_text)

# Callback query handler
@bot.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    if data == "start_login":
        await callback.message.edit_text(
            "🔐 **Starting Login Process**\n\n"
            "Please send your phone number with country code.\n"
            "Example: +1234567890\n\n"
            "Send /cancel to cancel."
        )
        user_manager.login_states[user_id] = "awaiting_phone"

    elif data == "view_plans":
        await plans_command(client, callback.message)

    elif data == "help":
        await help_command(client, callback.message)

    elif data == "upgrade_premium":
        await callback.message.edit_text(
            "💎 **Upgrade to Premium**\n\n"
            "Choose your plan:\n\n"
            "💰 Basic - ₹199/month\n"
            "🚀 Pro - ₹399/month\n"
            "⭐ Unlimited - ₹599/month\n\n"
            "Reply with: /upgrade <plan_name>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
            ])
        )

    await callback.answer()

# Message handler for login flow and ad setup
@bot.on_message(filters.private & ~filters.command(["start", "help", "login", "status", "plans"]))
async def message_handler(client: Client, message: Message):
    user_id = message.from_user.id

    # Handle login flow
    if user_id in user_manager.login_states:
        await user_manager.handle_login_flow(message)
        return

    # Handle ad setup
    # (Implementation continues in user_client.py)

# Main function
async def main():
    logger.info("🤖 Starting Telegram Ads Forwarding BOT...")

    # Create sessions directory
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    # Start bot
    await bot.start()
    logger.info("✅ Bot started successfully!")

    # Start user client manager
    await user_manager.start()

    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())