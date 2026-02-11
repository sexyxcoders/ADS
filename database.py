import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
import asyncio
from threading import Lock

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
            
            # Users table
            cursor.execute("""
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
                )
            """)
            
            # Groups table (for forwarding)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    group_id INTEGER,
                    group_name TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Ads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ad_text TEXT,
                    media_type TEXT,
                    media_file_id TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Owner ads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS owner_ads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_text TEXT,
                    media_type TEXT,
                    media_file_id TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Forwarding logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forwarding_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    group_id INTEGER,
                    group_name TEXT,
                    status TEXT,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    plan_type TEXT,
                    amount INTEGER,
                    payment_proof TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            conn.commit()
            conn.close()
    
    # User operations
    def add_user(self, user_id: int, username: str = None):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username)
                VALUES (?, ?)
            """, (user_id, username))
            conn.commit()
            conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
    
    def update_user_session(self, user_id: int, session_string: str, phone_number: str):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET session_string = ?, phone_number = ?
                WHERE user_id = ?
            """, (session_string, phone_number, user_id))
            conn.commit()
            conn.close()
    
    def update_user_premium(self, user_id: int, is_premium: bool, days: int = 30):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            expires = datetime.now() + timedelta(days=days) if is_premium else None
            cursor.execute("""
                UPDATE users 
                SET is_premium = ?, subscription_expires = ?
                WHERE user_id = ?
            """, (is_premium, expires, user_id))
            conn.commit()
            conn.close()
    
    def update_user_delay(self, user_id: int, delay_seconds: int):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET delay_seconds = ?
                WHERE user_id = ?
            """, (delay_seconds, user_id))
            conn.commit()
            conn.close()
    
    def set_user_active(self, user_id: int, is_active: bool):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_active = ?
                WHERE user_id = ?
            """, (is_active, user_id))
            conn.commit()
            conn.close()
    
    def set_log_channel(self, user_id: int, channel_id: int):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET log_channel_id = ?
                WHERE user_id = ?
            """, (channel_id, user_id))
            conn.commit()
            conn.close()
    
    def update_last_ad_run(self, user_id: int):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_ad_run = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            conn.close()
    
    # Group operations
    def add_group(self, user_id: int, group_id: int, group_name: str):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO user_groups (user_id, group_id, group_name)
                VALUES (?, ?, ?)
            """, (user_id, group_id, group_name))
            conn.commit()
            conn.close()
    
    def get_user_groups(self, user_id: int) -> List[Dict]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM user_groups WHERE user_id = ?
            """, (user_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    def remove_group(self, user_id: int, group_id: int):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_groups 
                WHERE user_id = ? AND group_id = ?
            """, (user_id, group_id))
            conn.commit()
            conn.close()
    
    # Ad operations
    def save_ad(self, user_id: int, ad_text: str, media_type: str = None, media_file_id: str = None):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ads SET is_active = 0 WHERE user_id = ?
            """, (user_id,))
            cursor.execute("""
                INSERT INTO ads (user_id, ad_text, media_type, media_file_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, ad_text, media_type, media_file_id))
            conn.commit()
            conn.close()
    
    def get_active_ad(self, user_id: int) -> Optional[Dict]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ads 
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
    
    # Owner ads
    def save_owner_ad(self, ad_text: str, media_type: str = None, media_file_id: str = None):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO owner_ads (ad_text, media_type, media_file_id)
                VALUES (?, ?, ?)
            """, (ad_text, media_type, media_file_id))
            conn.commit()
            ad_id = cursor.lastrowid
            conn.close()
            return ad_id
    
    def get_active_owner_ads(self) -> List[Dict]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM owner_ads WHERE is_active = 1
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    # Logs
    def add_forwarding_log(self, user_id: int, group_id: int, group_name: str, status: str, error: str = None):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO forwarding_logs (user_id, group_id, group_name, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, group_id, group_name, status, error))
            conn.commit()
            conn.close()
    
    # Get all active users
    def get_active_users(self) -> List[Dict]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users WHERE is_active = 1 AND session_string IS NOT NULL
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    # Get all free users
    def get_free_users(self) -> List[Dict]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users 
                WHERE is_active = 1 
                AND session_string IS NOT NULL
                AND (is_premium = 0 OR subscription_expires < CURRENT_TIMESTAMP)
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    # Payment operations
    def create_payment_request(self, user_id: int, plan_type: str, amount: int, payment_proof: str):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO payments (user_id, plan_type, amount, payment_proof)
                VALUES (?, ?, ?, ?)
            """, (user_id, plan_type, amount, payment_proof))
            conn.commit()
            payment_id = cursor.lastrowid
            conn.close()
            return payment_id
    
    def get_pending_payments(self) -> List[Dict]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, u.username 
                FROM payments p
                JOIN users u ON p.user_id = u.user_id
                WHERE p.status = 'pending'
                ORDER BY p.created_at DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    def approve_payment(self, payment_id: int):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE payments 
                SET status = 'approved', approved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (payment_id,))
            conn.commit()
            conn.close()

# ================= ASYNC COMPATIBILITY LAYER =================

class AsyncDatabase(Database):
    """
    Wrapper to make old sync Database work with new async architecture.
    No data loss. No rewrite needed.
    """

    async def init(self):
        # already initialized in __init__
        return

    async def add_user(self, *args, **kwargs):
        return await asyncio.to_thread(super().add_user, *args, **kwargs)

    async def get_user(self, *args, **kwargs):
        return await asyncio.to_thread(super().get_user, *args, **kwargs)

    async def update_user_session(self, *args, **kwargs):
        return await asyncio.to_thread(super().update_user_session, *args, **kwargs)

    async def update_user_premium(self, *args, **kwargs):
        return await asyncio.to_thread(super().update_user_premium, *args, **kwargs)

    async def update_user_delay(self, *args, **kwargs):
        return await asyncio.to_thread(super().update_user_delay, *args, **kwargs)

    async def set_user_active(self, *args, **kwargs):
        return await asyncio.to_thread(super().set_user_active, *args, **kwargs)

    async def get_user_groups(self, *args, **kwargs):
        return await asyncio.to_thread(super().get_user_groups, *args, **kwargs)

    async def get_active_ad(self, *args, **kwargs):
        return await asyncio.to_thread(super().get_active_ad, *args, **kwargs)

    async def save_ad(self, *args, **kwargs):
        return await asyncio.to_thread(super().save_ad, *args, **kwargs)

    async def get_active_users(self):
        return await asyncio.to_thread(super().get_active_users)

    async def get_free_users(self):
        return await asyncio.to_thread(super().get_free_users)

    async def close(self):
        return