import re
import time
import asyncio
from collections import defaultdict, deque

# -----------------------------
# SAFE INT
# -----------------------------
def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# -----------------------------
# INPUT SANITIZER
# -----------------------------
def sanitize_input(text: str, max_length: int = 4000) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"[<>]", "", text)  # prevent html injection
    return text[:max_length]


# -----------------------------
# ANTI FLOOD CLASS
# -----------------------------
class AntiFlood:
    def __init__(self, limit=5, per_seconds=10):
        self.limit = limit
        self.per_seconds = per_seconds
        self.users = defaultdict(deque)

    def check(self, user_id):
        now = time.time()
        q = self.users[user_id]

        while q and now - q[0] > self.per_seconds:
            q.popleft()

        if len(q) >= self.limit:
            return False

        q.append(now)
        return True


# -----------------------------
# RATE LIMIT CHECK (ASYNC SAFE)
# -----------------------------
rate_limits = defaultdict(lambda: {"last": 0, "cooldown": 3})

async def rate_limit_check(user_id: int, cooldown: int = 3):
    now = time.time()
    last = rate_limits[user_id]["last"]

    if now - last < cooldown:
        return False

    rate_limits[user_id]["last"] = now
    return True


# -----------------------------
# GET USER GROUPS FROM ACCOUNT
# (for user session clients)
# -----------------------------
async def get_user_groups_from_account(client):
    groups = []
    try:
        async for dialog in client.get_dialogs():
            if dialog.chat.type in ["group", "supergroup"]:
                groups.append({
                    "id": dialog.chat.id,
                    "title": dialog.chat.title
                })
    except Exception as e:
        print("Group fetch error:", e)
    return groups