import aiosqlite

DB_PATH = "botdata.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            telegram_name TEXT,
            email TEXT DEFAULT '',
            ovo_id TEXT DEFAULT '',
            ovo_amount TEXT DEFAULT '',
            credits INTEGER DEFAULT 0
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

async def get_ovo_id(user_id: int) -> str | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT ovo_id FROM users WHERE id = $1",
            user_id,
        )
        if row and row['ovo_id']:
            return row['ovo_id']
        return None

