import time
from collections import defaultdict


class AntiFlood:
    def __init__(self, limit=5, time_window=10):
        self.limit = limit
        self.time_window = time_window
        self.users = defaultdict(list)

    def check(self, user_id):
        now = time.time()
        timestamps = self.users[user_id]

        # Remove old timestamps
        self.users[user_id] = [t for t in timestamps if now - t < self.time_window]

        # Add new action
        self.users[user_id].append(now)

        if len(self.users[user_id]) > self.limit:
            return False  # Flooding
        return True