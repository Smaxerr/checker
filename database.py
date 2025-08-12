# database.py
import sqlite3
from typing import Optional, Dict

DB_FILE = "data/users.db"

def _connect():
    conn = sqlite3.connect(DB_FILE, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    import os
    os.makedirs("data", exist_ok=True)
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        telegram_name TEXT,
        email TEXT DEFAULT '',
        ovo_id TEXT DEFAULT '',
        ovo_amount TEXT DEFAULT '',
        credits INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def add_user_if_not_exists(telegram_id: int, telegram_name: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (telegram_id, telegram_name) VALUES (?, ?)", (telegram_id, telegram_name))
    conn.commit()
    conn.close()

def get_user(telegram_id: int) -> Optional[Dict]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_field(telegram_id: int, field: str, value: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field} = ? WHERE telegram_id = ?", (value, telegram_id))
    conn.commit()
    conn.close()

def add_credits(telegram_id: int, amount: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET credits = credits + ? WHERE telegram_id = ?", (amount, telegram_id))
    conn.commit()
    conn.close()

def deduct_credits_if_enough(telegram_id: int, amount: int) -> bool:
    """
    Atomically check credits and deduct 'amount'. Returns True if deduction happened.
    """
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT credits FROM users WHERE telegram_id = ?", (telegram_id,))
        r = cur.fetchone()
        if not r:
            conn.rollback()
            return False
        credits = r["credits"]
        if credits >= amount:
            cur.execute("UPDATE users SET credits = credits - ? WHERE telegram_id = ?", (amount, telegram_id))
            conn.commit()
            return True
        else:
            conn.rollback()
            return False
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_users() -> list:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY telegram_id")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
