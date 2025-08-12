import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
import aiosqlite

# State for email input
class SettingsStates(StatesGroup):
    waiting_for_email = State()

API_TOKEN = "7580204485:AAE1f-PP9Fx4S2eEWxSLjd0C_-bgzFcWXBo"
ADMIN_ID = 8159560233

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Database filename
DB_NAME = "users.db"

# Main Menu Keyboard
main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Ovo Charger", callback_data="ovo")],
    [InlineKeyboardButton(text="Royalmail Charger", callback_data="royalmail")],
    [InlineKeyboardButton(text="Settings", callback_data="settings")],
])

# Settings Keyboard
settings_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Change Email", callback_data="set_email")],
    [InlineKeyboardButton(text="Change Ovo ID", callback_data="set_ovo_id")],
    [InlineKeyboardButton(text="Change Ovo Amount", callback_data="set_ovo_amount")],
    [InlineKeyboardButton(text="Back to Main Menu", callback_data="back_main")],
])

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT,
                ovo_id TEXT,
                ovo_amount TEXT,
                credits INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def add_user_if_not_exists(user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM users WHERE telegram_id = ?", (user_id,))
        exists = await cursor.fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO users(telegram_id, username, credits) VALUES (?, ?, ?)",
                (user_id, username, 0)
            )
            await db.commit()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await add_user_if_not_exists(message.from_user.id, message.from_user.username or "")
    await message.answer(
        f"Welcome, <b>{message.from_user.full_name}</b>!\nChoose an option below:",
        reply_markup=main_kb,
    )

@dp.callback_query(lambda c: c.data == "back_main")
async def back_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("Main Menu:", reply_markup=main_kb)

@dp.callback_query(lambda c: c.data == "settings")
async def settings_menu(callback: CallbackQuery):
    await callback.message.edit_text("Settings Menu:", reply_markup=settings_kb)

# Handlers for settings changes - simplified example with FSM or state management recommended
# For brevity, not fully implemented here

@dp.callback_query(lambda c: c.data == "ovo")
async def ovo_charger_start(callback: CallbackQuery):
    await callback.message.edit_text("Send your test card(s) in format:\ncardnumber|expirymonth|expiryyear|cvv\nOne per line.")

@dp.message(F.text)
async def process_ovo_cards(message: Message):
    # Here you should check if user is currently entering ovo cards (needs FSM, omitted for brevity)
    # Example: For demo, just reply with received cards
    cards = message.text.strip().split("\n")
    await message.answer(f"Received {len(cards)} card(s). Processing now...")

    # TODO: Call your ovocharger.py async functions here with asyncio.gather()
    # Charge credits if success, refund if fail

@dp.callback_query(lambda c: c.data == "royalmail")
async def royalmail_charger_start(callback: CallbackQuery):
    await callback.message.edit_text("Send your test card(s) in format:\ncardnumber|expirymonth|expiryyear|cvv\nOne per line.")

@dp.message(F.text)
async def process_royalmail_cards(message: Message):
    # Similar as above, differentiate by user state or context
    pass

# Admin commands
@dp.message(Command("addbalance"))
async def admin_add_balance(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ You are not authorized to use this command.")
        return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Usage: /addbalance <TELEGRAM_ID> <AMOUNT>")
        return
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("Invalid arguments. IDs and amount must be numbers.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET credits = credits + ? WHERE telegram_id = ?", (amount, target_id))
        await db.commit()
    await message.answer(f"✅ Added {amount} credits to user {target_id}")

@dp.message(Command("viewusers"))
async def admin_view_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ You are not authorized to use this command.")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT telegram_id, username, email, ovo_id, ovo_amount, credits FROM users")
        rows = await cursor.fetchall()
    content = "telegram_id, username, email, ovo_id, ovo_amount, credits\n"
    for row in rows:
        content += ",".join(str(x) if x is not None else "" for x in row) + "\n"
    await message.answer_document(document=content.encode("utf-8"), filename="users.csv")

# Callback handler for Change Email button
@dp.callback_query(F.data == "change_email")
async def change_email_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter your new email address:")
    await state.set_state(SettingsStates.waiting_for_email)
    await callback.answer()

# Message handler to save new email
@dp.message(SettingsStates.waiting_for_email)
async def save_new_email(message: Message, state: FSMContext):
    new_email = message.text.strip()

    # You might want to add some basic email validation here
    # Example: check if '@' in new_email
    if "@" not in new_email:
        await message.answer("❌ That doesn't look like a valid email. Try again:")
        return

    # Save email to database
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET email = ? WHERE user_id = ?", (new_email, message.from_user.id))
        await db.commit()

    await message.answer(f"✅ Your email has been updated to: {new_email}")
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())








