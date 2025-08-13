import aiosqlite
import asyncio
import os

DB_PATH = "users.db"  # change if your DB is in another folder

async def add_column():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at: {os.path.abspath(DB_PATH)}")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Check existing columns
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await cursor.fetchall()]
        print("Current columns:", columns)

        # Add the column if missing
        if "screenshots_enabled" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN screenshots_enabled INTEGER DEFAULT 1"
            )
            await db.commit()
            print("✅ Column 'screenshots_enabled' added.")
        else:
            print("ℹ️ Column already exists.")

if __name__ == "__main__":
    asyncio.run(add_column())
