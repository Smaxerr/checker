# bot.py
import os
import sys
import asyncio
import base64
import io
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State

from database import init_db, add_user_if_not_exists, get_user, update_user_field, deduct_credits_if_enough, add_credits, get_all_users
import config

BOT_TOKEN = config.BOT_TOKEN
ADMIN_IDS = config.ADMIN_IDS
PYTHON_EXEC = config.PYTHON_EXECUTABLE or sys.executable

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("Please set your BOT_TOKEN in config.py")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

# FSM states
class SettingsStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_ovo_id = State()
    waiting_for_ovo_amount = State()
    waiting_for_settings_line = State()

class ChargerStates(StatesGroup):
    waiting_for_cards = State()

# remember which charger user selected
USER_PENDING_JOB = {}

# keyboards
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Ovo Charger"), types.KeyboardButton("Royalmail Charger"))
    kb.add(types.KeyboardButton("Settings"))
    return kb

def settings_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Edit Email"), types.KeyboardButton("Edit Ovo ID"))
    kb.add(types.KeyboardButton("Edit Ovo Amount"), types.KeyboardButton("Back to Main"))
    return kb

@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    init_db()
    add_user_if_not_exists(m.from_user.id, m.from_user.full_name)
    await m.answer("Welcome — choose an option:", reply_markup=main_kb())

# Settings menu
@dp.message(lambda message: message.text == "Settings")
async def settings_menu(message: types.Message):
    await message.answer("Settings menu:", reply_markup=settings_kb())

@dp.message(lambda message: message.text == "Edit Email")
async def edit_email(message: types.Message, state: FSMContext):
    await message.answer("Send your new Email (single line):")
    await state.set_state(SettingsStates.waiting_for_email)

@dp.message(SettingsStates.waiting_for_email)
async def save_email(message: types.Message, state: FSMContext):
    update_user_field(message.from_user.id, "email", message.text.strip())
    await state.clear()
    await message.answer("✅ Email updated.", reply_markup=settings_kb())

@dp.message(lambda message: message.text == "Edit Ovo ID")
async def edit_ovo_id(message: types.Message, state: FSMContext):
    await message.answer("Send your new Ovo ID (single line):")
    await state.set_state(SettingsStates.waiting_for_ovo_id)

@dp.message(SettingsStates.waiting_for_ovo_id)
async def save_ovo_id(message: types.Message, state: FSMContext):
    update_user_field(message.from_user.id, "ovo_id", message.text.strip())
    await state.clear()
    await message.answer("✅ Ovo ID updated.", reply_markup=settings_kb())

@dp.message(lambda message: message.text == "Edit Ovo Amount")
async def edit_ovo_amount(message: types.Message, state: FSMContext):
    await message.answer("Send your new Ovo Amount (single line):")
    await state.set_state(SettingsStates.waiting_for_ovo_amount)

@dp.message(SettingsStates.waiting_for_ovo_amount)
async def save_ovo_amount(message: types.Message, state: FSMContext):
    update_user_field(message.from_user.id, "ovo_amount", message.text.strip())
    await state.clear()
    await message.answer("✅ Ovo Amount updated.", reply_markup=settings_kb())

@dp.message(lambda message: message.text == "Back to Main")
async def back_to_main(message: types.Message):
    await message.answer("Main menu:", reply_markup=main_kb())

# Charger selection
@dp.message(lambda message: message.text == "Ovo Charger")
async def start_ovo(message: types.Message, state: FSMContext):
    USER_PENDING_JOB[message.from_user.id] = "ovocharger.py"
    await message.answer(
        "Send card(s) — one per line in format:\ncardnumber|mm|yyyy|cvv\n\n"
        "Example:\n4242424242424242|12|2026|123\n\n"
        "Multiple lines = multiple jobs. Each job costs 1 credit on success.\n", 
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(ChargerStates.waiting_for_cards)

@dp.message(lambda message: message.text == "Royalmail Charger")
async def start_royalmail(message: types.Message, state: FSMContext):
    USER_PENDING_JOB[message.from_user.id] = "royalmailcharger.py"
    await message.answer(
        "Send card(s) — one per line in format:\ncardnumber|mm|yyyy|cvv\n\n"
        "Multiple lines = multiple jobs. Each job costs 1 credit on success.\n",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(ChargerStates.waiting_for_cards)

async def run_script_get_screenshot(script_name: str, card_line: str, user: dict) -> tuple[bool, bytes, str]:
    """
    Run the script as subprocess, expecting base64 PNG on stdout when successful.
    Returns (success, image_bytes or b'', error_text)
    """
    args = [PYTHON_EXEC, script_name, card_line, user.get("email",""), user.get("ovo_id",""), user.get("ovo_amount","")]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0 and stdout:
        try:
            b64 = stdout.decode()
            img = base64.b64decode(b64)
            return True, img, ""
        except Exception as e:
            return False, b"", f"decoding error: {e}"
    else:
        err = stderr.decode().strip() or stdout.decode().strip()
        return False, b"", err or f"returncode {proc.returncode}"

@dp.message(ChargerStates.waiting_for_cards)
async def handle_cards(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("User not found. Please /start.")
        await state.clear()
        return

    lines = [l.strip() for l in message.text.splitlines() if l.strip()]
    if not lines:
        await message.answer("No card lines detected. Cancelling.", reply_markup=main_kb())
        await state.clear()
        return

    count = len(lines)
    # check & deduct upfront
    ok = deduct_credits_if_enough(user_id, count)
    if not ok:
        await message.answer(f"Insufficient credits. You need {count} credits to run {count} job(s). Use /addbalance (admins) or get credits.", reply_markup=main_kb())
        await state.clear()
        return

    await message.answer(f"Running {count} job(s) concurrently... (you were charged {count} credits up front; failed jobs will be refunded).", reply_markup=main_kb())

    script = USER_PENDING_JOB.get(user_id, "ovocharger.py")
    # schedule tasks
    tasks = [run_script_get_screenshot(script, line, user) for line in lines]
    results = await asyncio.gather(*tasks)

    # process results: for failures, refund 1 credit each; for success — send image
    refunds = 0
    for idx, (success, img_bytes, err) in enumerate(results, start=1):
        if success:
            # send photo to user
            bio = io.BytesIO(img_bytes)
            bio.name = f"screenshot_{idx}.png"
            bio.seek(0)
            caption = f"Job {idx} success."
            try:
                await bot.send_photo(user_id, photo=bio, caption=caption)
            except Exception as e:
                # if sending fails, refund
                refunds += 1
        else:
            refunds += 1
            await message.answer(f"Job {idx} failed: {err}")

    if refunds:
        add_credits(user_id, refunds)
        await message.answer(f"Refunded {refunds} credit(s) due to failures.")

    await state.clear()

# Admin: addbalance
@dp.message(Command("addbalance"))
async def cmd_addbalance(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ You are not an admin.")
        return
    try:
        parts = message.text.split()
        if len(parts) != 3:
            raise ValueError()
        _, tg_id_s, amount_s = parts
        tg_id = int(tg_id_s)
        amount = int(amount_s)
        add_credits(tg_id, amount)
        await message.answer(f"✅ Added {amount} credits to {tg_id}.")
    except Exception:
        await message.answer("Usage: /addbalance <telegram_id> <amount>")

# Admin: viewusers -> sends users.txt
@dp.message(Command("viewusers"))
async def cmd_viewusers(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ You are not an admin.")
        return
    rows = get_all_users()
    lines = []
    for r in rows:
        lines.append(f"{r['telegram_id']}\t{r['telegram_name']}\tcredits:{r['credits']}\temail:{r['email']}\tovo_id:{r['ovo_id']}\tovo_amount:{r['ovo_amount']}")
    txt = "\n".join(lines) or "no users"
    await bot.send_document(message.from_user.id, types.InputFile(io.BytesIO(txt.encode()), filename="users.txt"))

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
