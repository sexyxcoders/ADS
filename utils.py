from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
import logging

logger = logging.getLogger(__name__)

async def check_channel_membership(client: Client, user_id: int, channel_username: str) -> bool:
    """Check if user is member of a channel"""
    try:
        member = await client.get_chat_member(channel_username, user_id)
        return member.status in ["member", "administrator", "creator"]
    except UserNotParticipant:
        return False
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return True  # Allow if we can't check

def format_time(seconds: int) -> str:
    """Format seconds into human readable time"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"

def format_price(amount: int, currency: str = "₹") -> str:
    """Format price with currency"""
    return f"{currency}{amount}"

async def get_user_groups_from_account(client: Client) -> list:
    """Get all groups where user is member"""
    groups = []
    try:
        async for dialog in client.get_dialogs():
            if dialog.chat.type in ["group", "supergroup"]:
                groups.append({
                    'id': dialog.chat.id,
                    'title': dialog.chat.title,
                    'username': dialog.chat.username
                })
    except Exception as e:
        logger.error(f"Error getting user groups: {e}")

    return groups