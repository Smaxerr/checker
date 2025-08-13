import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


async def init_db():
    global db
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        telegram_name TEXT,
        email TEXT DEFAULT '',
        ovo_id TEXT DEFAULT '',
        ovo_amount TEXT DEFAULT '',
        credits INTEGER DEFAULT 10,
        screenshots_enabled INTEGER DEFAULT 1  -- 1 = True, 0 = False
    )
    """)
    await db.commit()

async def get_user(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row

async def add_or_update_user(telegram_id, telegram_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, telegram_name) VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET telegram_name=excluded.telegram_name
        """, (telegram_id, telegram_name))
        await db.commit()

async def update_user_field(telegram_id, field, value):
    if field not in ("email", "ovo_id", "ovo_amount"):
        raise ValueError("Invalid field")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE telegram_id = ?", (value, telegram_id))
        await db.commit()

async def change_credits(telegram_id, delta):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET credits = credits + ? WHERE telegram_id = ?", (delta, telegram_id))
        await db.commit()

async def get_credits(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT credits FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users") as cursor:
            return await cursor.fetchall()


async def get_ovo_id(telegram_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ovo_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]  # ovo_id value
            return None


async def get_ovo_amount(telegram_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ovo_amount FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]  # ovo_amount value
            return None


async def get_email(telegram_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT email FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]  # email value
            return None


async def get_screenshots_setting(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT screenshots_enabled FROM users WHERE telegram_id = ?", 
            (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return bool(row[0])
            return True  # default to True if user not found

async def set_screenshots_setting(telegram_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET screenshots_enabled = ? WHERE telegram_id = ?",
            (1 if enabled else 0, telegram_id)
        )
        await db.commit()









