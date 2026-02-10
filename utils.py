from pyrogram import Client
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
import time

logger = logging.getLogger(__name__)

# =========================================================
# 🔒 FORCE JOIN CHECK (FULLY FIXED)
# =========================================================
async def check_channel_membership(client: Client, user_id: int, channel: str) -> bool:
    """
    Returns True if user is currently a participant of the channel.
    Handles restricted users and all Telegram edge cases.
    """
    channel = extract_chat_id(channel)
    max_retries = 2

    for attempt in range(max_retries):
        try:
            member = await client.get_chat_member(channel, user_id)
            status = member.status

            # ✅ Valid participants
            if status in ("member", "administrator", "creator", "restricted"):
                logger.info(f"✅ User {user_id} is in {channel} (status: {status})")
                return True

            # ❌ Definitely not participant
            if status in ("left", "kicked"):
                logger.info(f"❌ User {user_id} not in {channel} (status: {status})")
                return False

            logger.warning(f"⚠️ Unknown status for {user_id} in {channel}: {status}")
            return False

        except UserNotParticipant:
            logger.info(f"👤 User {user_id} never joined {channel}")
            return False

        except ChatAdminRequired:
            logger.error("🚨 Bot must be ADMIN with 'View Members' permission in force-join channel!")
            return False

        except (PeerIdInvalid, UsernameNotOccupied):
            logger.error(f"❌ Invalid channel username: {channel}")
            return False

        except ChannelPrivate:
            logger.error(f"🔒 Bot has no access to private channel {channel}")
            return False

        except FloodWait as e:
            logger.warning(f"⏳ FloodWait {e.value}s...")
            await asyncio.sleep(e.value)
            continue

        except Exception as e:
            logger.error(f"⚠️ Membership check error (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue

    logger.error("❌ Membership check failed after retries")
    return False


# =========================================================
# ⏱ TIME FORMATTER
# =========================================================
def format_time(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    if seconds < 60:
        return f"{seconds}s"

    minutes, secs = divmod(seconds, 60)
    if seconds < 3600:
        return f"{minutes}m{'' if secs == 0 else f' {secs}s'}"

    hours, minutes = divmod(minutes, 60)
    if seconds < 86400:
        return f"{hours}h{'' if minutes == 0 else f' {minutes}m'}"

    days, hours = divmod(hours, 24)
    return f"{days}d{'' if hours == 0 else f' {hours}h'}"


# =========================================================
# 💰 PRICE FORMATTER
# =========================================================
def format_price(amount: int, currency: str = "₹") -> str:
    return f"{currency}{amount:,}"


# =========================================================
# 👥 GET USER GROUPS
# =========================================================
async def get_user_groups_from_account(client: Client) -> list:
    groups = []

    try:
        async for dialog in client.get_dialogs(limit=500):
            chat = dialog.chat

            if chat.type not in ("group", "supergroup"):
                continue

            if getattr(chat, "members_count", 0) < 5:
                continue

            group_info = {
                "chat_id": str(chat.id),
                "title": (chat.title or "Unnamed Group")[:100],
                "username": chat.username,
                "type": chat.type,
                "members_count": getattr(chat, "members_count", 0),
                "date_added": int(time.time())
            }

            if chat.username:
                group_info["permalink"] = f"https://t.me/{chat.username}"

            groups.append(group_info)

        groups.sort(key=lambda x: x["members_count"], reverse=True)
        logger.info(f"✅ Found {len(groups)} viable groups")
        return groups

    except Exception as e:
        logger.error(f"❌ Error fetching groups: {e}")
        return []


# =========================================================
# 🔗 CHAT ID NORMALIZER
# =========================================================
def extract_chat_id(input_str: str) -> str:
    if not input_str:
        return ""

    s = input_str.strip()

    if s.startswith("@"):
        return s

    if "t.me/" in s:
        path = s.split("t.me/")[1].split("/")[0].split("?")[0]
        return path if path.startswith("+") else f"@{path}"

    if s.startswith("-"):
        return s

    if re.match(r'^[a-zA-Z0-9_\.]+$', s):
        return f"@{s}"

    return s


# =========================================================
# 📱 PHONE VALIDATION
# =========================================================
def is_valid_phone(phone: str) -> tuple[bool, str]:
    if not phone:
        return False, "Phone number required"

    phone = phone.strip().replace(" ", "").replace("-", "")

    if not phone.startswith("+"):
        return False, "Must start with country code (+XX)"

    if not re.match(r'^\+[1-9]\d{7,14}$', phone):
        return False, "Invalid format"

    return True, phone


# =========================================================
# 🧹 CLEAN MESSAGE TEXT
# =========================================================
def clean_message_text(text: str, max_len: int = 4096) -> str:
    if not text:
        return ""

    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'\n{3,}', '\n\n', text)

    if len(text) > max_len:
        text = text[:max_len - 12] + "\n\n...[truncated]"

    return text


# =========================================================
# 📊 STATS FORMATTER
# =========================================================
def format_stats(value: int, unit: str = "") -> str:
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M{unit}"
    if value >= 1_000:
        return f"{value/1_000:.0f}K{unit}"
    return f"{value:,}{unit}"


# =========================================================
# 🎯 MAIN MENU KEYBOARD
# =========================================================
def get_main_keyboard(is_premium=False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🔐 Login Account", callback_data="start_login")],
        [InlineKeyboardButton("📊 Status", callback_data="show_status")]
    ]

    if is_premium:
        buttons.append([InlineKeyboardButton("⚙️ Settings", callback_data="settings")])

    buttons += [
        [InlineKeyboardButton("💎 Upgrade", callback_data="view_plans")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")]
    ]

    return InlineKeyboardMarkup(buttons)


# =========================================================
# 🔍 SEARCH GROUPS
# =========================================================
def search_groups(groups: list, query: str) -> list:
    if not query:
        return groups
    q = query.lower()
    return [g for g in groups if q in g.get("title", "").lower() or q in str(g.get("username", "")).lower()]


# =========================================================
# 📈 SUCCESS RATE
# =========================================================
def success_rate(success: int, total: int) -> float:
    return round((success / total * 100), 1) if total else 0.0


# =========================================================
# 🧪 TEST MODE
# =========================================================
if __name__ == "__main__":
    print("🧪 Running utils tests...")
    print(format_time(3661))
    print(format_price(125000))
    print(extract_chat_id("t.me/testgroup"))
    print(is_valid_phone("+919876543210"))
    print("✅ Done")