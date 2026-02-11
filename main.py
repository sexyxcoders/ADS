#!/usr/bin/env python3
"""
Telegram Ads Forwarding BOT
Main entry point with all handlers integrated
No Force Join Required
"""

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from datetime import datetime

from config import *
from database import Database
from user_client import UserClientManager
from handlers import AdHandler, GroupHandler, AutomationHandler, DelayHandler, UpgradeHandler
from admin_handlers import AdminHandler
from advanced_handlers import AdvancedCommandHandlers

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
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

# Initialize handlers
ad_handler = AdHandler(bot, db, user_manager)
group_handler = GroupHandler(bot, db, user_manager)
automation_handler = AutomationHandler(bot, db, user_manager)
delay_handler = DelayHandler(bot, db)
upgrade_handler = UpgradeHandler(bot, db)
admin_handler = AdminHandler(bot, db, user_manager, OWNER_ID)
advanced_handlers = AdvancedCommandHandlers(bot, db, user_manager)

# ============ BOT COMMANDS ============

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

**✨ NEW FEATURES:**
📊 Advanced Analytics
🔄 Ad Rotation
⏰ Scheduled Campaigns
🎁 Referral Program
📝 Ad Templates

**Quick Start:**
1. /login - Connect account
2. /templates - Choose ad template
3. /setad - Set your ad
4. /addgroups - Add groups
5. /start_ads - Start automation!

**Popular Commands:**
/analytics - View performance
/myads - Manage ads
/referral - Earn free premium
/templates - Ad templates
/help - All commands
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Login Now", callback_data="login_now")],
        [InlineKeyboardButton("📝 View Templates", callback_data="show_templates")],
        [InlineKeyboardButton("💎 Premium Plans", callback_data="show_plans")]
    ])

    await message.reply_text(welcome_text, reply_markup=keyboard, disable_web_page_preview=True)

@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    help_text = """
📖 **Complete Command Guide**

**🔐 Account:**
/login - Login with Telegram session
/logout - Logout from bot
/status - Check status & statistics
/checkhealth - Check session health

**📢 Advertisement:**
/setad - Set your advertisement
/viewad - View current ad
/myads - View all your ads
/togglead - Enable/disable ad
/autorotate - Enable ad rotation

**👥 Group Management:**
/addgroups - Auto-add all your groups
/listgroups - View all added groups
/removegroup - Remove specific group
/pausegroup - Pause specific group
/resumegroup - Resume paused group
/vipgroup - Set group priority
/groupstats - View group statistics

**⚙️ Automation:**
/start_ads - Start forwarding
/stop_ads - Stop forwarding
/schedule - Schedule campaign

**📊 Analytics & Reports:**
/analytics - View detailed analytics
/report - Daily report
/weeklyreport - Weekly report

**💎 Premium:**
/delay - Set custom delay
/plans - View plans
/upgrade - Upgrade account

**🎁 Referral:**
/referral - View referral program

**📝 Templates:**
/templates - Browse templates
/template - View template

**👨‍💼 Admin:**
/stats - Bot statistics
/payments - Pending payments
/approve - Approve payment
/reject - Reject payment
/ownerads - Save promotional ad
/broadcast - Broadcast owner ad
/broadcasttext - Broadcast message
    """
    await message.reply_text(help_text, disable_web_page_preview=True)

@bot.on_message(filters.command("login") & filters.private)
async def login_command(client: Client, message: Message):
    user_id = message.from_user.id

    user = db.get_user(user_id)
    if user and user['session_string']:
        await message.reply_text(
            "✅ You're already logged in!\n\n"
            "Use /logout to logout and login again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Logout", callback_data="do_logout")]
            ])
        )
        return

    login_text = """
🔐 **Login to Your Telegram Account**

**How it works:**
1. You send your phone number
2. Telegram sends you an OTP code
3. You enter the code here
4. Your session is saved securely

**Security:**
✅ Session stored encrypted
✅ We never access your messages
✅ Logout anytime with /logout

**Ready?** Send your phone number with country code.
Example: +1234567890

Send /cancel to cancel anytime.
    """

    await message.reply_text(login_text, disable_web_page_preview=True)
    user_manager.login_states[user_id] = "awaiting_phone"

@bot.on_message(filters.command("logout") & filters.private)
async def logout_command(client: Client, message: Message):
    user_id = message.from_user.id

    # Stop automation
    db.set_user_active(user_id, False)
    await user_manager.stop_automation(user_id)

    # Disconnect session
    if user_id in user_manager.active_sessions:
        try:
            await user_manager.active_sessions[user_id].stop()
            del user_manager.active_sessions[user_id]
        except:
            pass

    # Remove from database
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET session_string = NULL, is_active = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    await message.reply_text(
        "✅ **Logged Out Successfully!**\n\n"
        "Your session has been removed.\n"
        "Use /login to login again.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Login Again", callback_data="login_now")]
        ])
    )

@bot.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        await message.reply_text("❌ User not found. Use /start first.")
        return

    if not user['session_string']:
        await message.reply_text(
            "❌ Not logged in. Use /login to get started.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Login", callback_data="login_now")]
            ])
        )
        return

    groups = db.get_user_groups(user_id)
    ad = db.get_active_ad(user_id)

    is_premium = user['is_premium'] and user['subscription_expires'] and \
                 datetime.fromisoformat(user['subscription_expires']) > datetime.now()

    status_text = f"""
📊 **Your Status**

👤 **Account:**
• Phone: {user['phone_number'] or 'Not set'}
• Tier: {'🌟 Premium' if is_premium else '🆓 Free'}

📢 **Ad:** {'✅ Set' if ad else '❌ Not set'}
👥 **Groups:** {len(groups)}
⚙️ **Automation:** {'🟢 Running' if user['is_active'] else '🔴 Stopped'}
⏱️ **Delay:** {user['delay_seconds']}s

📈 **Subscription:**
    """

    if is_premium:
        expires = datetime.fromisoformat(user['subscription_expires'])
        days_left = (expires - datetime.now()).days
        status_text += f"• Expires: {expires.strftime('%Y-%m-%d')}\n• Days left: {days_left}"
    else:
        status_text += "• Free tier (5 min delay)\n• Upgrade: /plans"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")],
        [InlineKeyboardButton("⚙️ Manage Groups", callback_data="manage_groups")],
        [InlineKeyboardButton("💎 Upgrade", callback_data="show_plans")]
    ])

    await message.reply_text(status_text, reply_markup=keyboard, disable_web_page_preview=True)

# Ad commands
@bot.on_message(filters.command("setad") & filters.private)
async def setad_command(client: Client, message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user['session_string']:
        await message.reply_text(
            "❌ Please login first: /login",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Login", callback_data="login_now")]
            ])
        )
        return
    await ad_handler.start_ad_setup(message)

@bot.on_message(filters.command("viewad") & filters.private)
async def viewad_command(client: Client, message: Message):
    ad = db.get_active_ad(message.from_user.id)
    if not ad:
        await message.reply_text("❌ No ad set. Use /setad to create one.")
        return

    if ad['media_type'] and ad['media_file_id']:
        if ad['media_type'] == 'photo':
            await message.reply_photo(ad['media_file_id'], caption=ad['ad_text'])
        elif ad['media_type'] == 'video':
            await message.reply_video(ad['media_file_id'], caption=ad['ad_text'])
    else:
        await message.reply_text(f"📢 **Your Ad:**\n\n{ad['ad_text']}")

# Group commands
@bot.on_message(filters.command("addgroups") & filters.private)
async def addgroups_command(client: Client, message: Message):
    await group_handler.add_groups_command(message)

@bot.on_message(filters.command("listgroups") & filters.private)
async def listgroups_command(client: Client, message: Message):
    await group_handler.list_groups_command(message)

# Automation commands
@bot.on_message(filters.command("start_ads") & filters.private)
async def start_ads_command(client: Client, message: Message):
    await automation_handler.start_ads_command(message)

@bot.on_message(filters.command("stop_ads") & filters.private)
async def stop_ads_command(client: Client, message: Message):
    await automation_handler.stop_ads_command(message)

# Premium commands
@bot.on_message(filters.command("delay") & filters.private)
async def delay_command(client: Client, message: Message):
    await delay_handler.delay_command(message)

@bot.on_message(filters.command("plans") & filters.private)
async def plans_command(client: Client, message: Message):
    plans_text = """
💎 **Premium Plans**

**🆓 Free Plan:**
• Unlimited groups
• 5 minutes delay
• Forced footer
• Owner ads enabled
• Bio/Name locked

**💰 Basic - ₹199/month:**
• Unlimited groups
• 10s - 10min delay
• No footer
• No owner ads
• Free bio/name

**🚀 Pro - ₹399/month:**
• All Basic features
• Priority support
• Advanced analytics

**⭐ Unlimited - ₹599/month:**
• All Pro features
• Fastest forwarding
• Dedicated support

**Upgrade:** /upgrade <plan>
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade Now", callback_data="upgrade_menu")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")]
    ])
    
    await message.reply_text(plans_text, reply_markup=keyboard, disable_web_page_preview=True)

@bot.on_message(filters.command("upgrade") & filters.private)
async def upgrade_command(client: Client, message: Message):
    await upgrade_handler.upgrade_command(message)

# Admin commands
@bot.on_message(filters.command("stats") & filters.private & filters.user(OWNER_ID))
async def stats_command(client: Client, message: Message):
    await admin_handler.stats_command(message)

@bot.on_message(filters.command("payments") & filters.private & filters.user(OWNER_ID))
async def payments_command(client: Client, message: Message):
    await admin_handler.payments_command(message)

@bot.on_message(filters.command("approve") & filters.private & filters.user(OWNER_ID))
async def approve_command(client: Client, message: Message):
    await admin_handler.approve_command(message)

@bot.on_message(filters.command("reject") & filters.private & filters.user(OWNER_ID))
async def reject_command(client: Client, message: Message):
    await admin_handler.reject_command(message)

@bot.on_message(filters.command("ownerads") & filters.private & filters.user(OWNER_ID))
async def ownerads_command(client: Client, message: Message):
    await admin_handler.ownerads_command(message)

@bot.on_message(filters.command("broadcast") & filters.private & filters.user(OWNER_ID))
async def broadcast_command(client: Client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /broadcast <ad_id>")
        return

    try:
        ad_id = int(args[1])
        await message.reply_text(f"🚀 Broadcasting ad #{ad_id}...")
        await user_manager.broadcast_owner_ad(ad_id)
        await message.reply_text("✅ Broadcast completed!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("broadcasttext") & filters.private & filters.user(OWNER_ID))
async def broadcasttext_command(client: Client, message: Message):
    await admin_handler.broadcast_text_command(message)

# ============ ADVANCED FEATURES COMMANDS ============

# Analytics Commands
@bot.on_message(filters.command("analytics") & filters.private)
async def analytics_command(client: Client, message: Message):
    await advanced_handlers.analytics_command(message)

@bot.on_message(filters.command("report") & filters.private)
async def report_command(client: Client, message: Message):
    await advanced_handlers.report_command(message)

@bot.on_message(filters.command("weeklyreport") & filters.private)
async def weeklyreport_command(client: Client, message: Message):
    await advanced_handlers.weeklyreport_command(message)

# Ad Management Commands
@bot.on_message(filters.command("myads") & filters.private)
async def myads_command(client: Client, message: Message):
    await advanced_handlers.myads_command(message)

@bot.on_message(filters.command("togglead") & filters.private)
async def togglead_command(client: Client, message: Message):
    await advanced_handlers.togglead_command(message)

@bot.on_message(filters.command("autorotate") & filters.private)
async def autorotate_command(client: Client, message: Message):
    await advanced_handlers.autorotate_command(message)

# Group Management Commands
@bot.on_message(filters.command("pausegroup") & filters.private)
async def pausegroup_command(client: Client, message: Message):
    await advanced_handlers.pausegroup_command(message)

@bot.on_message(filters.command("resumegroup") & filters.private)
async def resumegroup_command(client: Client, message: Message):
    await advanced_handlers.resumegroup_command(message)

@bot.on_message(filters.command("vipgroup") & filters.private)
async def vipgroup_command(client: Client, message: Message):
    await advanced_handlers.vipgroup_command(message)

@bot.on_message(filters.command("groupstats") & filters.private)
async def groupstats_command(client: Client, message: Message):
    await advanced_handlers.groupstats_command(message)

# Referral Command
@bot.on_message(filters.command("referral") & filters.private)
async def referral_command(client: Client, message: Message):
    await advanced_handlers.referral_command(message)

# Template Commands
@bot.on_message(filters.command("templates") & filters.private)
async def templates_command(client: Client, message: Message):
    await advanced_handlers.templates_command(message)

@bot.on_message(filters.command("template") & filters.private)
async def template_command(client: Client, message: Message):
    await advanced_handlers.template_command(message)

# Health Check Command
@bot.on_message(filters.command("checkhealth") & filters.private)
async def checkhealth_command(client: Client, message: Message):
    await advanced_handlers.checkhealth_command(message)

# Schedule Command
@bot.on_message(filters.command("schedule") & filters.private)
async def schedule_command(client: Client, message: Message):
    await advanced_handlers.schedule_command(message)

# ============ CALLBACK HANDLERS ============

@bot.on_callback_query()
async def callback_handler(client: Client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data == "login_now":
        await login_command(client, callback_query.message)
    elif data == "show_templates":
        await templates_command(client, callback_query.message)
    elif data == "show_plans":
        await plans_command(client, callback_query.message)
    elif data == "do_logout":
        await logout_command(client, callback_query.message)
    elif data == "refresh_status":
        await status_command(client, callback_query.message)
    elif data == "manage_groups":
        await listgroups_command(client, callback_query.message)
    elif data == "show_help":
        await help_command(client, callback_query.message)
    elif data.startswith("analytics_"):
        days = data.split("_")[1]
        if days == "all":
            days = 365
        else:
            days = int(days)

        text = await advanced_handlers.show_analytics(user_id, days)
        await callback_query.message.edit_text(text)
    elif data == "upgrade_menu":
        await upgrade_command(client, callback_query.message)

    await callback_query.answer()

# Message handler for flows
@bot.on_message(filters.private & ~filters.command([
    "start", "help", "login", "logout", "status", "setad", "viewad", 
    "addgroups", "listgroups", "start_ads", "stop_ads", "delay", 
    "plans", "upgrade", "stats", "payments", "approve", "reject",
    "ownerads", "broadcast", "broadcasttext", "analytics", "report",
    "weeklyreport", "myads", "togglead", "autorotate", "pausegroup",
    "resumegroup", "vipgroup", "groupstats", "referral", "templates",
    "template", "checkhealth", "schedule"
]))
async def message_handler(client: Client, message: Message):
    user_id = message.from_user.id

    # Handle login flow
    if user_id in user_manager.login_states:
        await user_manager.handle_login_flow(message)
        return

    # Handle ad setup
    if user_id in ad_handler.ad_setup_state:
        await ad_handler.handle_ad_message(message)
        return

    # Handle owner ad setup
    if user_id == OWNER_ID and user_id in admin_handler.owner_ad_state:
        await admin_handler.handle_owner_ad(message)
        return

    # Handle payment proof
    if user_id in upgrade_handler.upgrade_state and message.photo:
        await upgrade_handler.handle_payment_proof(message)
        return

    # Default response for unknown commands
    await message.reply_text(
        "❓ Unknown command. Use /help to see all available commands.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Help", callback_data="show_help")]
        ])
    )

# Main function
async def main():
    logger.info("=" * 60)
    logger.info("🤖 Starting Telegram Ads Forwarding BOT")
    logger.info("🚀 No Force Join - Instant Access!")
    logger.info("=" * 60)

    # Create sessions directory
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    logger.info(f"📁 Sessions directory: {SESSIONS_DIR}")

    # Start bot
    logger.info("🔄 Starting bot client...")
    await bot.start()
    me = await bot.get_me()
    logger.info(f"✅ Bot started: @{me.username} (ID: {me.id})")

    # Start user client manager
    logger.info("🔄 Loading user sessions...")
    await user_manager.start()
    logger.info(f"✅ Loaded {len(user_manager.active_sessions)} active sessions")

    logger.info("=" * 60)
    logger.info("🎉 BOT IS FULLY READY!")
    logger.info("📱 Users can start immediately with /start")
    logger.info("=" * 60)

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)