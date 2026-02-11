from pyrogram.errors import FloodWait
import asyncio

async def get_user_groups_from_account(user_client):
    """
    Fetch all groups where user account is member/admin
    """
    groups = []

    try:
        async for dialog in user_client.get_dialogs():
            try:
                chat = dialog.chat

                # Only groups & supergroups
                if chat.type in ("group", "supergroup"):
                    groups.append({
                        "id": chat.id,
                        "title": chat.title
                    })

            except FloodWait as e:
                await asyncio.sleep(e.value)

            except Exception:
                continue

    except Exception as e:
        print(f"Group fetch error: {e}")

    return groups