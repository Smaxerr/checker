import logging
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters.command import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import database
from ovocharger import run_ovocharger
from royalmailcharger import run_royalmailcharger

API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Put your Telegram admin IDs here
ADMINS = {123456789, 987654321}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

class MainMenuCD(CallbackData, prefix="menu"):
    action: str

class SettingsStates(StatesGroup):
    waiting_for_field = State()
    waiting_for_value = State()

class OvoChargerStates(StatesGroup):
    waiting_for_cards = State()

class RoyalMailChargerStates(StatesGroup):
    waiting_for_cards = State()

# Keyboards
def main_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ovo Charger", callback_data=MainMenuCD(action="ovo"))],
        [InlineKeyboardButton(text="Royalmail Charger", callback_data=MainMenuCD(action="royalmail"))],
        [InlineKeyboardButton(text="Settings", callback_data=MainMenuCD(action="settings"))]
    ])
    return kb

def settings_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Edit Email", callback_data="edit_email")],
        [InlineKeyboardButton(text="Edit Ovo ID", callback_data="edit_ovoid")],
        [InlineKeyboardButton(text="Edit Ovo Amount", callback_data="edit_ovoamount")],
        [InlineKeyboardButton(text="Back to Menu", callback_data="back_main")]
    ])
    return kb

@dp.message(Command(commands=["start"]))
async def cmd_start(message: Message):
    await database.add_or_update_user(message.from_user.id, message.from_user.full_name)
    user_data = await database.get_user(message.from_user.id)
    credits = user_data[5] if user_data else 0
    await message.answer(
        f"Welcome, <b>{message.from_user.full_name}</b>!\nCredits: <b>{credits}</b>",
        reply_markup=main_menu_kb()
    )

@dp.callback_query(MainMenuCD.filter())
async def main_menu_handler(callback: CallbackQuery, callback_data: MainMenuCD, state: FSMContext):
    await callback.answer()
    if callback_data.action == "ovo":
        await callback.message.answer("Please send your test card details (format: cardnumber|expirymonth|expiryyear|cvv). You can send multiple lines.")
        await state.set_state(OvoChargerStates.waiting_for_cards)
    elif callback_data.action == "royalmail":
        await callback.message.answer("Please send your test card details for Royalmail (format: cardnumber|expirymonth|expiryyear|cvv). Multiple lines allowed.")
        await state.set_state(RoyalMailChargerStates.waiting_for_cards)
    elif callback_data.action == "settings":
        await callback.message.edit_text("Settings Menu:", reply_markup=settings_kb())

@dp.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Main Menu:", reply_markup=main_menu_kb())

@dp.callback_query(F.data.startswith("edit_"))
async def edit_setting(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    field = callback.data.split("_")[1]  # email, ovoid, ovoamount
    await state.update_data(field=field)
    await callback.message.answer(f"Send new value for <b>{field}</b>:")
    await state.set_state(SettingsStates.waiting_for_value)

@dp.message(SettingsStates.waiting_for_value)
async def save_setting(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("field")
    value = message.text.strip()
    await database.update_user_field(message.from_user.id, field, value)
    await message.answer(f"Updated {field} to: <b>{value}</b>")
    await message.answer("Back to main menu:", reply_markup=main_menu_kb())
    await state.clear()

@dp.message(OvoChargerStates.waiting_for_cards)
async def handle_ovocharger_cards(message: Message, state: FSMContext):
    cards = message.text.strip().splitlines()
    user_data = await database.get_user(message.from_user.id)
    credits = user_data[5] if user_data else 0
    if credits < len(cards):
        await message.answer(f"Insufficient credits. You have {credits} credits but sent {len(cards)} cards.")
        await state.clear()
        return

    await message.answer(f"Processing {len(cards)} Ovo cards, this may take a while...")

    async def run_card(card):
        result, screenshot = await run_ovocharger(card)
        text = f"Card: <code>{card}</code>\nResult: {result}"
        if screenshot:
            await bot.send_photo(message.chat.id, screenshot, caption=text)
        else:
            await message.answer(text)

    await asyncio.gather(*[run_card(card) for card in cards])

    await database.change_credits(message.from_user.id, -len(cards))
    await message.answer("Done! Credits deducted.", reply_markup=main_menu_kb())
    await state.clear()

@dp.message(RoyalMailChargerStates.waiting_for_cards)
async def handle_royalmailcharger_cards(message: Message, state: FSMContext):
    cards = message.text.strip().splitlines()
    user_data = await database.get_user(message.from_user.id)
    credits = user_data[5] if user_data else 0
    if credits < len(cards):
        await message.answer(f"Insufficient credits. You have {credits} credits but sent {len(cards)} cards.")
        await state.clear()
        return

    await message.answer(f"Processing {len(cards)} Royalmail cards, this may take a while...")

    async def run_card(card):
        result, screenshot = await run_royalmailcharger(card)
        text = f"Card: <code>{card}</code>\nResult: {result}"
        if screenshot:
            await bot.send_photo(message.chat.id, screenshot, caption=text)
        else:
            await message.answer(text)

    await asyncio.gather(*[run_card(card) for card in cards])

    await database.change_credits(message.from_user.id, -len(cards))
    await message.answer("Done! Credits deducted.", reply_markup=main_menu_kb())
    await state.clear()

# Admin commands

@dp.message(Command(commands=["addbalance"]))
async def cmd_addbalance(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("You are not authorized to use this command.")
        return
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        amount = int(parts[2])
    except (IndexError, ValueError):
        await message.answer("Usage: /addbalance TELEGRAMID AMOUNT")
        return

    await database.change_credits(target_id, amount)
    await message.answer(f"Added {amount} credits to user {target_id}.")

@dp.message(Command(commands=["viewusers"]))
async def cmd_viewusers(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("You are not authorized to use this command.")
        return

    users = await database.get_all_users()
    lines = []
    for u in users:
        # u = (telegram_id, telegram_name, email, ovo_id, ovo_amount, credits)
        lines.append(f"{u[0]}\t{u[1]}\t{u[2]}\t{u[3]}\t{u[4]}\t{u[5]}")

    txt = "\n".join(lines)
    await message.answer_document(("users.txt", txt.encode()))

async def main():
    await database.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
