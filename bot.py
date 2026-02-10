import os
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import (
    FloodWait, UserNotParticipant, ChatAdminRequired, UsernameNotOccupied, 
    ChannelPrivate, PeerIdInvalid, ChatMemberStatus
)
from datetime import datetime, timedelta
import logging

from config import *
from database import Database
from user_client import UserClientManager
from utils import (
    check_channel_membership, format_time, log_success, log_error, 
    log_info, log_warning, extract_chat_id
)

# Setup logging
logging.basicConfig(
    level=logging.INFO if not DEBUG_MODE else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize components
bot = Client("ads_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = Database()
user_manager = UserClientManager(bot, db)

# Global state
force_join_pending_users = set()
login_states = {}

# ===========================================
# 🔒 FORCE JOIN SYSTEM (PRODUCTION READY)
# ===========================================
async def get_channel_join_link():
    """Get proper channel join link"""
    if FORCE_JOIN_LINK and FORCE_JOIN_LINK.startswith("http"):
        return FORCE_JOIN_LINK
    channel = FORCE_JOIN_CHANNEL.lstrip('@')
    return f"https://t.me/{channel}"

async def is_user_member(client: Client, user_id: int, channel_id: str) -> bool:
    """✅ FIXED: Handle ALL ChatMemberStatus types"""
    try:
        member = await client.get_chat_member(channel_id, user_id)
        status = member.status
        
        # ✅ FIXED: Handle ALL valid statuses
        valid_statuses = {
            "member", "administrator", "creator", 
            ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, 
            ChatMemberStatus.OWNER, ChatMemberStatus.CREATOR
        }
        
        is_valid = status in valid_statuses or "member" in str(status).lower()
        
        if is_valid:
            log_success(f"User {user_id} verified in {channel_id}")
            return True
            
        log_warning(f"Invalid status '{status}' for {user_id} in {channel_id}")
        return False
        
    except UserNotParticipant:
        log_info(f"User {user_id} not participant in {channel_id}")
        return False
    except (ChatAdminRequired, PeerIdInvalid, UsernameNotOccupied, ChannelPrivate):
        log_error(f"Channel error {channel_id}: {type(e).__name__}")
        return False
    except FloodWait as e:
        log_warning(f"FloodWait {e.value}s for {user_id}")
        await asyncio.sleep(e.value)
        return False
    except Exception as e:
        log_error(f"Membership check failed: {e}")
        return False

async def force_join_check(client: Client, user_id: int, message: Message = None) -> bool:
    """Comprehensive force join with timeout tracking"""
    try:
        # Skip for owner
        if user_id == OWNER_ID:
            return True
            
        channel_id = FORCE_JOIN_CHANNEL
        is_member = await check_channel_membership(client, user_id, channel_id)
        
        if not is_member:
            join_link = await get_channel_join_link()
            channel_display = FORCE_JOIN_CHANNEL.replace('@', '')
            
            join_text = (
                f"🔒 **Join Required**\n\n"
                f"📢 **Channel:** {channel_display}\n\n"
                f"👇 **Join first, then /start**\n\n"
                f"⏰ **Timeout:** {FORCE_JOIN_TIMEOUT_MINUTES}min"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=join_link)],
                [InlineKeyboardButton("🔄 Verify", callback_data=f"verify_join_{user_id}")]
            ])
            
            force_join_pending_users.add(user_id)
            
            target = message.reply_text if message else lambda t, **k: client.send_message(user_id, t, **k)
            await target(join_text, reply_markup=keyboard, disable_web_page_preview=True)
            
            # Schedule timeout
            asyncio.create_task(join_timeout(user_id))
            return False
        
        # ✅ Member verified
        force_join_pending_users.discard(user_id)
        return True
        
    except Exception as e:
        log_error(f"Force join error {user_id}: {e}")
        return False

async def join_timeout(user_id: int):
    """Auto-remove after timeout"""
    await asyncio.sleep(FORCE_JOIN_TIMEOUT_MINUTES * 60)
    force_join_pending_users.discard(user_id)
    log_info(f"Timeout expired for pending user {user_id}")

# ===========================================
# 🎯 MAIN COMMANDS
# ===========================================
@bot.on_message(filters.command("start") & filters.private)
async def cmd_start(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    # Always save user
    db.add_user(user_id, username)
    
    # Force join check
    if not await force_join_check(client, user_id, message):
        return
    
    # Welcome screen
    user_data = db.get_user(user_id) or {}
    is_premium = user_data.get("is_premium", False)
    
    welcome = (
        f"🤖 **Welcome {username}!**\n\n"
        f"👤 `ID:` `{user_id}`\n"
        f"⭐ **Plan:** {'💎 Premium' if is_premium else '🆓 Free'}\n\n"
        "**🚀 Get Started:**\n"
        f"• `/login` - Link account\n"
        f"• `/status` - Dashboard\n"
        f"• `/plans` - Upgrade"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Login", callback_data="login_phone")],
        [InlineKeyboardButton("📊 Status", callback_data="user_status")],
        [InlineKeyboardButton("💎 Plans", callback_data="show_plans")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")]
    ])
    
    await message.reply_text(welcome, reply_markup=keyboard, parse_mode="markdown")

@bot.on_message(filters.command(["help", "menu"]) & filters.private)
async def cmd_help(client: Client, message: Message):
    if not await force_join_check(client, message.from_user.id, message):
        return
        
    help_text = """
📖 **Commands:**

🔐 **Account**
`/login` `/status` `/logout`

📢 **Ads**
`/setad` `/viewad` `/clearad`

👥 **Groups**  
`/addgroups` `/listgroups` `/removegroup`

⚙️ **Control**
`/start_ads` `/stop_ads` `/delay <seconds>`

💎 **Premium**
`/plans` `/upgrade`
    """
    
    await message.reply_text(help_text)

# ===========================================
# 📊 STATUS & DASHBOARD
# ===========================================
@bot.on_message(filters.command("status") & filters.private)
async def cmd_status(client: Client, message: Message):
    if not await force_join_check(client, message.from_user.id, message):
        return
        
    await show_dashboard(client, message, message.from_user.id)

async def show_dashboard(client: Client, context, user_id: int):
    """Unified dashboard"""
    user = db.get_user(user_id) or {}
    groups = len(db.get_user_groups(user_id))
    has_ad = bool(db.get_active_ad(user_id))
    is_running = user.get("is_active", False)
    
    dashboard = (
        f"📊 **Dashboard**\n\n"
        f"👤 **User:** `{user_id}`\n"
        f"📱 **Phone:** `{user.get('phone', 'Not logged in')}`\n"
        f"⭐ **Plan:** {'💎 Premium' if user.get('is_premium') else '🆓 Free'}\n\n"
        f"📢 **Ad:** {'✅ Set' if has_ad else '❌ None'}\n"
        f"👥 **Groups:** `{groups}`\n"
        f"⚙️ **Status:** {'🟢 Live' if is_running else '🔴 Stopped'}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="user_status")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")],
        [InlineKeyboardButton("🔙 Home", callback_data="main_menu")]
    ])
    
    if isinstance(context, Message):
        await context.reply_text(dashboard, reply_markup=keyboard, parse_mode="markdown")
    else:
        await context.edit_text(dashboard, reply_markup=keyboard, parse_mode="markdown")

# ===========================================
# 💎 PLANS & UPGRADE
# ===========================================
@bot.on_message(filters.command("plans") & filters.private)
async def cmd_plans(client: Client, message: Message):
    if not await force_join_check(client, message.from_user.id, message):
        return
    
    plans_text = "💎 **Subscription Plans**\n\n"
    for plan_id, plan in PRICING.items():
        plans_text += f"**{plan['name']}** - ₹{plan['price']}/mo\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Buy Now", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ])
    
    await message.reply_text(plans_text, reply_markup=keyboard, parse_mode="markdown")

# ===========================================
# 👑 ADMIN COMMANDS
# ===========================================
@bot.on_message(filters.command(["stats", "broadcast"]) & filters.user(OWNER_ID))
async def admin_cmds(client: Client, message: Message):
    if message.command[0] == "stats":
        users = len(db.get_all_users())
        active = len([u for u in db.get_all_users() if u.get("is_active")])
        premium = len([u for u in db.get_all_users() if u.get("is_premium")])
        
        stats = (
            f"📊 **Admin Stats**\n\n"
            f"👥 **Total:** `{users}`\n"
            f"🟢 **Active:** `{active}`\n"
            f"💎 **Premium:** `{premium}`"
        )
        await message.reply_text(stats, parse_mode="markdown")
    
    elif message.command[0] == "broadcast":
        # Broadcast implementation
        pass

# ===========================================
# 🖱️ CALLBACK HANDLER (FIXED)
# ===========================================
@bot.on_callback_query()
async def cb_handler(client: Client, callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    
    try:
        if data.startswith("verify_join_"):
            if await force_join_check(client, user_id):
                await callback.message.delete()
                await cmd_start(client, callback.message)
            else:
                await callback.answer("❌ Join channel first!", show_alert=True)
                
        elif data == "login_phone":
            await callback.message.edit_text(
                "📱 **Enter Phone:**\n`+1234567890`\n\nSend now:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
                ]),
                parse_mode="markdown"
            )
            login_states[user_id] = "phone"
            
        elif data in ["user_status", "main_menu", "show_plans", "show_help"]:
            if data == "user_status":
                await show_dashboard(client, callback, user_id)
            elif data == "main_menu":
                await callback.message.delete()
                await cmd_start(client, callback.message)
            # Handle others...
            
        else:
            await callback.answer("⏳ Coming soon!")
            
    except Exception as e:
        log_error(f"Callback {data} error: {e}")
        await callback.answer("⚠️ Error occurred", show_alert=True)

# ===========================================
# 💬 MESSAGE HANDLER
# ===========================================
@bot.on_message(filters.private & ~filters.command(["start"]))
async def msg_handler(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Handle login flow
    if user_id in login_states:
        await user_manager.handle_login_flow(message)
        return
    
    # Force join pending
    if user_id in force_join_pending_users:
        await force_join_check(client, user_id, message)
        return
    
    # Auto-force join other commands
    await force_join_check(client, user_id, message)

# ===========================================
# 🚀 MAIN FUNCTION (FIXED)
# ===========================================
async def main():
    """Production startup"""
    log_info("🤖 Starting AdForward Bot...")
    
    # Cleanup
    startup_cleanup()
    
    # Start components
    await bot.start()
    log_success("✅ Bot connected!")
    
    await user_manager.start()
    log_success("✅ User manager ready!")
    
    log_success("🚀 Bot fully operational!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("👋 Bot stopped by user")
    except Exception as e:
        log_error(f"💥 Fatal error: {e}")