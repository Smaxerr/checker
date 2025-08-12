import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputFile
import aiosqlite

API_TOKEN = "7580204485:AAE1f-PP9Fx4S2eEWxSLjd0C_-bgzFcWXBo"
ADMIN_ID = 8159560233

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

DB_NAME = "users.db"

# Main and settings keyboards
main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Ovo Charger", callback_data="ovo")],
    [InlineKeyboardButton(text="Royalmail Charger", callback_data="royalmail")],
    [InlineKeyboardButton(text="Settings", callback_data="settings")],
])

settings_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Change Email", callback_data="set_email")],
    [InlineKeyboardButton(text="Change Ovo ID", callback_data="set_ovo_id")],
    [InlineKeyboardButton(text="Change Ovo Amount", callback_data="set_ovo_amount")],
    [InlineKeyboardButton(text="Back to Main Menu", callback_data="back_main")],
])

# FSM states for settings
class SettingsStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_ovo_id = State()
    waiting_for_ovo_amount = State()
    waiting_for_ovo_cards = State()
    waiting_for_royalmail_cards = State()

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

@dp.callback_query(F.data == "back_main")
async def back_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Main Menu:", reply_markup=main_kb)
    await state.clear()

@dp.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Settings Menu:", reply_markup=settings_kb)
    await state.clear()

# Settings handlers with FSM

@dp.callback_query(F.data == "set_email")
async def set_email(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter your new email:")
    await state.set_state(SettingsStates.waiting_for_email)
    await callback.answer()

@dp.message(SettingsStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.strip()
    # TODO: Validate email format if needed
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET email = ? WHERE telegram_id = ?", (email, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Email updated to: {email}")
    await state.clear()

@dp.callback_query(F.data == "set_ovo_id")
async def set_ovo_id(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter your new Ovo ID:")
    await state.set_state(SettingsStates.waiting_for_ovo_id)
    await callback.answer()

@dp.message(SettingsStates.waiting_for_ovo_id)
async def process_ovo_id(message: Message, state: FSMContext):
    ovo_id = message.text.strip()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ovo_id = ? WHERE telegram_id = ?", (ovo_id, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Ovo ID updated to: {ovo_id}")
    await state.clear()

@dp.callback_query(F.data == "set_ovo_amount")
async def set_ovo_amount(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter your new Ovo Amount:")
    await state.set_state(SettingsStates.waiting_for_ovo_amount)
    await callback.answer()

@dp.message(SettingsStates.waiting_for_ovo_amount)
async def process_ovo_amount(message: Message, state: FSMContext):
    ovo_amount = message.text.strip()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ovo_amount = ? WHERE telegram_id = ?", (ovo_amount, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Ovo Amount updated to: {ovo_amount}")
    await state.clear()

# Ovo Charger flow FSM

@dp.callback_query(F.data == "ovo")
async def ovo_charger_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Send your test card(s) in format:\ncardnumber|expirymonth|expiryyear|cvv\nOne per line.")
    await state.set_state(SettingsStates.waiting_for_ovo_cards)
    await callback.answer()

@dp.message(SettingsStates.waiting_for_ovo_cards)
async def process_ovo_cards(message: Message, state: FSMContext):
    cards = message.text.strip().split("\n")
    await message.answer(f"Received {len(cards)} card(s). Processing now...")
    # TODO: call your async charge functions here
    await state.clear()

# Royalmail Charger flow FSM

@dp.callback_query(F.data == "royalmail")
async def royalmail_charger_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Send your test card(s) in format:\ncardnumber|expirymonth|expiryyear|cvv\nOne per line.")
    await state.set_state(SettingsStates.waiting_for_royalmail_cards)
    await callback.answer()

@dp.message(SettingsStates.waiting_for_royalmail_cards)
async def process_royalmail_cards(message: Message, state: FSMContext):
    cards = message.text.strip().split("\n")
    await message.answer(f"Received {len(cards)} Royalmail card(s). Processing now...")
    # TODO: call your async charge functions here
    await state.clear()

@dp.message(Command("viewusers"))
async def view_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ You are not authorized to use this command.")
        return

    filename = "users_list.txt"
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT telegram_id, username, email, ovo_id, ovo_amount, credits FROM users")
        rows = await cursor.fetchall()

    # Write user data to file
    with open(filename, "w", encoding="utf-8") as f:
        for row in rows:
            line = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}\n"
            f.write(line)

    input_file = InputFile(path=filename)
    await message.answer_document(input_file, caption=f"Users list ({len(rows)} users)")

    # Clean up the file after sending
    os.remove(filename)



async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



