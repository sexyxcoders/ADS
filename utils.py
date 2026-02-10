from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid
import logging

logger = logging.getLogger(__name__)


# 🔒 FORCE JOIN CHECK (STRICT)
async def check_channel_membership(client: Client, user_id: int, channel: str) -> bool:
    """
    Returns True ONLY if user is a member.
    Returns False for all failures (safe-side).
    """
    try:
        member = await client.get_chat_member(channel, user_id)

        if member.status in ("member", "administrator", "creator"):
            return True

        return False

    except UserNotParticipant:
        # User did not join
        return False

    except ChatAdminRequired:
        # Bot is not admin in channel
        logger.error("❌ Bot must be ADMIN in force join channel with 'See Members' permission.")
        return False

    except PeerIdInvalid:
        # Wrong username or channel ID
        logger.error("❌ Invalid channel username/ID for force join.")
        return False

    except Exception as e:
        # Any API or unexpected error
        logger.error(f"⚠️ Membership check failed: {e}")
        return False


# ⏱ TIME FORMATTER
def format_time(seconds: int) -> str:
    """Convert seconds into readable format"""
    if seconds < 60:
        return f"{seconds} seconds"

    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"


# 💰 PRICE FORMATTER
def format_price(amount: int, currency: str = "₹") -> str:
    return f"{currency}{amount}"


# 👥 GET GROUPS FROM USER ACCOUNT
async def get_user_groups_from_account(client: Client) -> list:
    """
    Fetch all groups/supergroups where user account is present
    (Used for ad forwarding accounts, NOT bot)
    """
    groups = []

    try:
        async for dialog in client.get_dialogs():
            chat = dialog.chat

            if chat.type in ("group", "supergroup"):
                groups.append({
                    "id": chat.id,
                    "title": chat.title,
                    "username": chat.username
                })

    except Exception as e:
        logger.error(f"Error getting user groups: {e}")

    return groups