import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from threading import Lock


# =========================================================
# CORE DATABASE (SYNC SQLITE)
# =========================================================
class Database:
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path
        self.lock = Lock()
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                phone_number TEXT,
                session_string TEXT,
                is_premium BOOLEAN DEFAULT 0,
                subscription_expires TIMESTAMP,
                delay_seconds INTEGER DEFAULT 300,
                is_active BOOLEAN DEFAULT 0,
                log_channel_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_ad_run TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                group_id INTEGER,
                group_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ad_text TEXT,
                media_type TEXT,
                media_file_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS owner_ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_text TEXT,
                media_type TEXT,
                media_file_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS forwarding_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                group_id INTEGER,
                group_name TEXT,
                status TEXT,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_type TEXT,
                amount INTEGER,
                payment_proof TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP
            );
            """)

            conn.commit()
            conn.close()

    # ---------------- USERS ----------------
    def add_user(self, user_id, username=None):
        with self.lock:
            conn = self.get_connection()
            conn.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            conn.commit()
            conn.close()

    def get_user(self, user_id) -> Optional[Dict]:
        with self.lock:
            conn = self.get_connection()
            row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
            conn.close()
            return dict(row) if row else None

    def set_user_active(self, user_id, active: bool):
        with self.lock:
            conn = self.get_connection()
            conn.execute("UPDATE users SET is_active=? WHERE user_id=?", (active, user_id))
            conn.commit()
            conn.close()

    def update_user_session(self, user_id, session, phone):
        with self.lock:
            conn = self.get_connection()
            conn.execute("UPDATE users SET session_string=?, phone_number=? WHERE user_id=?", (session, phone, user_id))
            conn.commit()
            conn.close()

    # ---------------- GROUPS ----------------
    def add_group(self, user_id, group_id, name):
        with self.lock:
            conn = self.get_connection()
            conn.execute("INSERT OR IGNORE INTO user_groups (user_id, group_id, group_name) VALUES (?, ?, ?)", (user_id, group_id, name))
            conn.commit()
            conn.close()

    def get_user_groups(self, user_id):
        with self.lock:
            conn = self.get_connection()
            rows = conn.execute("SELECT * FROM user_groups WHERE user_id=?", (user_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    # ---------------- ADS ----------------
    def save_ad(self, user_id, text, mtype=None, fid=None):
        with self.lock:
            conn = self.get_connection()
            conn.execute("UPDATE ads SET is_active=0 WHERE user_id=?", (user_id,))
            conn.execute("INSERT INTO ads (user_id, ad_text, media_type, media_file_id) VALUES (?, ?, ?, ?)",
                         (user_id, text, mtype, fid))
            conn.commit()
            conn.close()

    def get_active_ad(self, user_id):
        with self.lock:
            conn = self.get_connection()
            row = conn.execute("SELECT * FROM ads WHERE user_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1",
                               (user_id,)).fetchone()
            conn.close()
            return dict(row) if row else None

    # ---------------- USERS LIST ----------------
    def get_active_users(self):
        with self.lock:
            conn = self.get_connection()
            rows = conn.execute("SELECT * FROM users WHERE is_active=1 AND session_string IS NOT NULL").fetchall()
            conn.close()
            return [dict(r) for r in rows]


# =========================================================
# ASYNC WRAPPER
# =========================================================
class AsyncDatabase(Database):
    async def _run(self, fn, *args):
        return await asyncio.to_thread(fn, *args)

    async def add_user(self, *a): return await self._run(super().add_user, *a)
    async def get_user(self, *a): return await self._run(super().get_user, *a)
    async def set_user_active(self, *a): return await self._run(super().set_user_active, *a)
    async def update_user_session(self, *a): return await self._run(super().update_user_session, *a)
    async def get_user_groups(self, *a): return await self._run(super().get_user_groups, *a)
    async def save_ad(self, *a): return await self._run(super().save_ad, *a)
    async def get_active_ad(self, *a): return await self._run(super().get_active_ad, *a)
    async def get_active_users(self): return await self._run(super().get_active_users)


# =========================================================
# LEGACY COMPAT WRAPPER
# =========================================================
class DatabaseConnection:
    """Old handlers expect this class"""
    def __init__(self, path="bot_database.db"):
        self.db = AsyncDatabase(path)

    async def add_user(self, *a): return await self.db.add_user(*a)
    async def get_user(self, *a): return await self.db.get_user(*a)
    async def set_user_active(self, *a): return await self.db.set_user_active(*a)
    async def get_user_groups(self, *a): return await self.db.get_user_groups(*a)
    async def save_ad(self, *a): return await self.db.save_ad(*a)
    async def get_active_ad(self, *a): return await self.db.get_active_ad(*a)
    async def get_active_users(self): return await self.db.get_active_users()