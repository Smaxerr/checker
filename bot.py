import os
import asyncio

from ovocharger import run_ovocharger
from royalmailcharger import run_royalmailcharger

from aiogram import Bot, Dispatcher, F
from io import BytesIO
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.types import BotCommand
import tempfile
from aiogram.fsm.context import FSMContext
from aiogram.types import InputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandObject
from aiogram import types
from aiogram.types import BufferedInputFile
from aiogram.types import FSInputFile
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

HELP_TEXT = """
🤖 *Bot Setup & Usage Guide*

1️⃣ *Setup your settings first:*
- Set your *email* in the Settings.
- Set your *OVO ID*.
- Set the *amount* you want per operation.

2️⃣ *How to use the bot:*
- Use the commands or menus.
- Input format:
  cardnumber|expirymonth|expiryyear|cvv
If you use any other format, bot may fail.

3️⃣ *Costs:*
- Each operation costs 1 credit deducted from your balance.
- Ensure you have enough balance before running scripts.

4️⃣ *Commands:*
- /start - View balance and menu.
- /help - Show this message.
- Settings - Update your details.

Contact @smaxxxer for support.
"""

async def help_command(message: types.Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown")

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
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT username, ovo_amount FROM users WHERE telegram_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

    if row is None:
        username = message.from_user.username or message.from_user.full_name
        credits = 0
        # Optionally insert user into DB here if needed
    else:
        username, credits = row
        if not username:
            username = message.from_user.username or message.from_user.full_name
        if credits is None:
            credits = 0

    text = (
        f"Welcome to SmaxChex, @{username}.\n"
        f"You have {credits} Credits remaining.\n\n"
        "Use the menu below to continue"
    )

    # Assuming you have a main_menu_kb defined somewhere
    await message.answer(text, reply_markup=main_kb)
    
@dp.callback_query(F.data == "back_main")
async def back_main_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT username, ovo_amount FROM users WHERE telegram_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

    if row is None:
        username = callback.from_user.username or callback.from_user.full_name
        credits = 0
    else:
        username, credits = row
        if not username:
            username = callback.from_user.username or callback.from_user.full_name
        if credits is None:
            credits = 0

    text = (
        f"Welcome to SmaxChex, @{username}.\n"
        f"You have {credits} Credits remaining.\n\n"
        "Use the menu below to continue"
    )

    await callback.message.edit_text(text, reply_markup=main_kb)
    await state.clear()
    await callback.answer()
    
@dp.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT username, email, ovo_id, ovo_amount FROM users WHERE telegram_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

    if row is None:
        await callback.message.edit_text("⚠️ User data not found.")
        return

    username, email, ovo_id, ovo_amount = row

    profile_text = (
        "🛠️ <b>My Profile</b>\n\n"
        f"👤 Username: @{username if username else 'Not set'}\n"
        f"📧 Email: {email if email else 'Not set'}\n"
        f"🆔 OVO ID: {ovo_id if ovo_id else 'Not set'}\n"
        f"💰 OVO Amount: {ovo_amount if ovo_amount is not None else '0'}\n"
    )

    await callback.message.edit_text(profile_text, parse_mode="HTML", reply_markup=settings_kb)
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

    results = []
    for card in cards:
        # Run the ovocharger for each card and get result + screenshot
        result, screenshot_bytes = await run_ovocharger(card)

        if screenshot_bytes:
            # Write bytes to temp file and send photo
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                tmp.write(screenshot_bytes)
                tmp.flush()
                photo = FSInputFile(tmp.name)
                await message.answer_photo(photo=photo)

        results.append(f"{card}: {result}")

    await message.answer("\n".join(results))
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
    await message.answer(f"Received {len(cards)} card(s). Processing now...")

    results = []
    for card in cards:
        # Run the ovocharger for each card and get result + screenshot
        result, screenshot_bytes = await run_royalmailcharger(card)

        if screenshot_bytes:
            # Write bytes to temp file and send photo
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                tmp.write(screenshot_bytes)
                tmp.flush()
                photo = FSInputFile(tmp.name)
                await message.answer_photo(photo=photo)

        results.append(f"{card}: {result}")

    await message.answer("\n".join(results))
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

    with open(filename, "w", encoding="utf-8") as f:
        for row in rows:
            line = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}\n"
            f.write(line)

    file_to_send = FSInputFile(path=filename)
    await message.answer_document(file_to_send, caption=f"Users list ({len(rows)} users)")

    os.remove(filename)

@dp.message(Command("addbalance"))
async def add_balance(message: Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ You are not authorized to use this command.")
        return

    # command.args contains the full string after the command, e.g. "123456789 10"
    args = command.args.split()
    if len(args) != 2:
        await message.answer("Usage: ./addbalance <telegram_id> <amount>")
        return

    try:
        user_id = int(args[0])
        amount = int(args[1])
    except ValueError:
        await message.answer("Please provide valid integers for telegram_id and amount.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT credits FROM users WHERE telegram_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await message.answer(f"User with telegram_id {user_id} not found.")
            return
        current_credits = row[0] or 0
        new_credits = current_credits + amount
        await db.execute("UPDATE users SET credits = ? WHERE telegram_id = ?", (new_credits, user_id))
        await db.commit()

    await message.answer(f"✅ Added {amount} credits to user {user_id}. New balance: {new_credits}")


@dp.message(Command("setbalance"))
async def set_balance(message: Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ You are not authorized to use this command.")
        return

    args = command.args.split()
    if len(args) != 2:
        await message.answer("Usage: ./setbalance <telegram_id> <amount>")
        return

    try:
        user_id = int(args[0])
        amount = int(args[1])
    except ValueError:
        await message.answer("Please provide valid integers for telegram_id and amount.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM users WHERE telegram_id = ?", (user_id,))
        user_exists = await cursor.fetchone()
        if not user_exists:
            await message.answer(f"User with telegram_id {user_id} not found.")
            return
        await db.execute("UPDATE users SET credits = ? WHERE telegram_id = ?", (amount, user_id))
        await db.commit()

    await message.answer(f"✅ Set user {user_id} balance to {amount}.")

async def main():
    await init_db()

    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help info"),
    ]
    await bot.set_my_commands(commands)

    dp.message.register(help_command, Command(commands=["help"]))

    await dp.start_polling(bot)
    
if __name__ == "__main__":
    asyncio.run(main())









































