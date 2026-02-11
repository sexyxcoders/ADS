"""
🧰 Utility Functions - Production Version
Used across handlers, admin, automation
"""

import time
import asyncio
from collections import defaultdict
from datetime import timedelta
from pyrogram.errors import FloodWait


# =========================================================
# 🚦 ANTI FLOOD SYSTEM
# =========================================================
class AntiFlood:
    def __init__(self, max_requests=5, window=timedelta(seconds=10)):
        self.max_requests = max_requests
        self.window = window.total_seconds()
        self.users = defaultdict(list)

    async def check(self, user_id: int) -> bool:
        now = time.time()

        # Remove expired timestamps
        self.users[user_id] = [
            t for t in self.users[user_id] if now - t < self.window
        ]

        # Add new request
        self.users[user_id].append(now)

        return len(self.users[user_id]) <= self.max_requests


# =========================================================
# 🔢 SAFE INT
# =========================================================
def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


# =========================================================
# 🧼 SANITIZE INPUT
# =========================================================
def sanitize_input(text):
    return str(text).strip()


# =========================================================
# 👥 FETCH USER GROUPS FROM USER ACCOUNT
# =========================================================
async def get_user_groups_from_account(user_client):
    groups = []

    try:
        async for dialog in user_client.get_dialogs():
            try:
                chat = dialog.chat
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