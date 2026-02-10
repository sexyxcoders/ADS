from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    UserNotParticipant, 
    ChatAdminRequired, 
    PeerIdInvalid,
    UsernameNotOccupied,
    ChannelPrivate,
    FloodWait
)
import logging
import asyncio
import re

logger = logging.getLogger(__name__)


# 🔒 FORCE JOIN CHECK (STRICT & PRODUCTION READY)
async def check_channel_membership(client: Client, user_id: int, channel: str) -> bool:
    """
    Returns True ONLY if user is a member.
    Returns False for all failures (safe-side).
    """
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Get chat member status
            member = await client.get_chat_member(channel, user_id)

            # Check membership status
            valid_statuses = ("member", "administrator", "creator")
            if member.status in valid_statuses:
                logger.info(f"✅ User {user_id} verified as member of {channel}")
                return True

            logger.info(f"❌ User {user_id} not member of {channel} (status: {member.status})")
            return False

        except UserNotParticipant:
            logger.info(f"👤 User {user_id} has not joined {channel}")
            return False

        except ChatAdminRequired:
            logger.error("🚨 BOT MUST BE ADMIN in force join channel with 'View Members' permission!")
            return False

        except (PeerIdInvalid, UsernameNotOccupied):
            logger.error(f"❌ INVALID CHANNEL: {channel}")
            return False

        except ChannelPrivate:
            logger.error(f"🔒 Channel {channel} is private/inaccessible")
            return False

        except FloodWait as e:
            logger.warning(f"⏳ Rate limited, waiting {e.value} seconds...")
            await asyncio.sleep(e.value)
            continue

        except Exception as e:
            logger.error(f"⚠️ Membership check error (attempt {attempt+1}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
    
    logger.error(f"❌ Membership check FAILED after {max_retries} attempts")
    return False


# ⏱ TIME FORMATTER (ENHANCED)
def format_time(seconds: int) -> str:
    """Convert seconds to human-readable format"""
    if seconds <= 0:
        return "0s"
    
    if seconds < 60:
        return f"{seconds}s"
    
    minutes = seconds // 60
    secs = seconds % 60
    
    if seconds < 3600:
        return f"{minutes}m{'' if secs == 0 else f' {secs}s'}"
    
    hours = minutes // 60
    minutes = minutes % 60
    
    if seconds < 86400:
        return f"{hours}h{minutes>0 and f' {minutes}m' or ''}"
    
    # Days
    days = hours // 24
    hours = hours % 24
    return f"{days}d{hours>0 and f' {hours}h' or ''}"


# 💰 PRICE FORMATTER
def format_price(amount: int, currency: str = "₹") -> str:
    """Format price with Indian numbering"""
    return f"{currency}{amount:,}"


# 👥 GET GROUPS FROM USER ACCOUNT (COMPLETE IMPLEMENTATION)
async def get_user_groups_from_account(client: Client) -> list:
    """
    Fetch all groups/supergroups where user is participant.
    Used for ad forwarding target selection.
    """
    groups = []
    
    try:
        logger.info("🔍 Fetching user dialogs...")
        
        async for dialog in client.get_dialogs(limit=500):
            chat = dialog.chat
            
            # Only groups & supergroups
            if chat.type in ("group", "supergroup"):
                # Skip tiny groups (less spam potential)
                try:
                    member_count = chat.members_count or 0
                    if member_count < 5:  # Minimum viable group size
                        continue
                except:
                    pass  # Continue if can't check member count
                
                group_info = {
                    "chat_id": str(chat.id),
                    "title": (chat.title or "Unnamed Group")[:100],
                    "username": chat.username,
                    "type": chat.type,
                    "members_count": getattr(chat, "members_count", 0),
                    "date_added": asyncio.get_event_loop().time()
                }
                
                # Generate invite/permalink
                if chat.username:
                    group_info["permalink"] = f"https://t.me/{chat.username}"
                
                groups.append(group_info)
        
        # Sort by member count (descending)
        groups.sort(key=lambda x: x.get("members_count", 0), reverse=True)
        logger.info(f"✅ Found {len(groups)} viable groups")
        
        return groups
        
    except Exception as e:
        logger.error(f"❌ Error fetching groups: {e}")
        return []


# 🔗 EXTRACT CHAT ID FROM VARIOUS FORMATS
def extract_chat_id(input_str: str) -> str:
    """Convert @username, t.me/link, or numeric ID to standard format"""
    if not input_str:
        return ""
    
    s = input_str.strip()
    
    # Already valid @username
    if s.startswith('@'):
        return s
    
    # t.me/username or t.me/+invite
    if 't.me/' in s:
        path = s.split('t.me/')[1].split('/')[0].split('?')[0]
        if path.startswith('+'):
            return path  # Invite link
        return f"@{path}"
    
    # Numeric chat ID
    if s.startswith('-'):
        return s
    
    # Assume username without @
    if s.replace('.', '').replace('_', '').isalnum():
        return f"@{s}"
    
    return s  # Return original


# ✅ PHONE NUMBER VALIDATION
def is_valid_phone(phone: str) -> tuple[bool, str]:
    """Validate & clean phone number"""
    if not phone:
        return False, "Phone number required"
    
    phone = phone.strip().replace(' ', '').replace('-', '')
    
    # Must start with +
    if not phone.startswith('+'):
        return False, "Must start with country code (+XX)"
    
    # Basic validation
    pattern = r'^\+[1-9]\d{7,14}$'
    if not re.match(pattern, phone):
        return False, "Invalid format (7-15 digits after +)"
    
    return True, phone


# 🧹 CLEAN & TRUNCATE MESSAGE TEXT
def clean_message_text(text: str, max_len: int = 4096) -> str:
    """Clean text for Telegram limits"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Truncate if needed
    if len(text) > max_len:
        text = text[:max_len-10] + "\n\n...[truncated]"
    
    return text


# 📊 FORMAT STATISTICS
def format_stats(value: int, unit: str = "") -> str:
    """1,234 → 1.2K, 1,234,567 → 1.2M"""
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M{unit}"
    elif value >= 1_000:
        return f"{value/1_000:.0f}K{unit}"
    return f"{value:,}{unit}"


# 🎯 MAIN MENU KEYBOARD
def get_main_keyboard(is_premium: bool = False, is_active: bool = False) -> InlineKeyboardMarkup:
    """Generate context-aware main menu"""
    buttons = [
        [InlineKeyboardButton("🔐 Login Account", callback_data="start_login")],
        [InlineKeyboardButton("📊 Status", callback_data="show_status")]
    ]
    
    if is_premium:
        buttons.insert(2, [InlineKeyboardButton("⚙️ Settings", callback_data="settings")])
    
    buttons.extend([
        [InlineKeyboardButton("💎 Upgrade", callback_data="view_plans")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")]
    ])
    
    return InlineKeyboardMarkup(buttons)


# 🔍 SEARCH GROUPS
def search_groups(groups: list, query: str) -> list:
    """Filter groups by title/username"""
    if not query:
        return groups
    
    q = query.lower()
    return [g for g in groups if q in g.get('title', '').lower() or q in g.get('username', '').lower()]


# 📈 SUCCESS RATE CALCULATION
def success_rate(success: int, total: int) -> float:
    """Safe percentage calculation"""
    return round((success / total * 100), 1) if total > 0 else 0.0


# LOGGING UTILITIES
def log_success(msg: str):
    logger.info(f"✅ {msg}")

def log_error(msg: str):
    logger.error(f"❌ {msg}")

def log_info(msg: str):
    logger.info(f"📝 {msg}")

def log_warning(msg: str):
    logger.warning(f"⚠️ {msg}")


# 🧪 TEST FUNCTIONS (RUN python utils.py to test)
async def test_utils():
    """Test all utility functions"""
    print("🧪 Testing utils.py...")
    
    # Test phone validation
    valid, cleaned = is_valid_phone("+919876543210")
    print(f"Phone: {valid} -> {cleaned}")
    
    # Test chat extraction
    tests = ["@testgroup", "t.me/testgroup", "-1001234567890", "testgroup"]
    for t in tests:
        print(f"Chat '{t}' -> '{extract_chat_id(t)}'")
    
    # Test time formatting
    for s in [30, 90, 3600, 86400]:
        print(f"{s}s -> {format_time(s)}")
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_utils())