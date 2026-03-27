import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from db import (
    init_db,
    add_reminder,
    get_due_reminders,
    get_all_users,
    mark_sent_once,
    mark_sent_recurring,
    update_reminder_type,
    get_user_reminders,
    delete_reminder_from_db,
    get_language,
    update_language,
    update_timezone_offset,
    get_timezone_offset,
)

import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("Environment variable TOKEN is not set")

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class Form(StatesGroup):
    waiting_for_message_time = State()
    waiting_for_message_reminder = State()
    waiting_for_message_set_time = State()
    waiting_for_message_type = State()
    waiting_for_message_delete_id = State()
    waiting_for_message_set_language = State()


db = None


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)
    await message.answer(text.start_message[lang])


@dp.message(Command("add"))
async def add_notification(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    message_text = message.text or ""
    parts_after_cmd = message_text.split(None, 1)
    args = parts_after_cmd[1].strip() if len(parts_after_cmd) > 1 else ""

    if args:
        parts = args.split(";", 1)
        if len(parts) == 2:
            time_str = parts[0].strip()
            reminder_text = parts[1].strip()
            try:
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                await message.answer(text.adding_1[lang])
                return

            rid = await add_reminder(db, user_id, time_str, reminder_text, rtype=0, pos=1)
            await message.answer(
                text.adding_2[lang].format(
                    rid=rid,
                    time_str=time_str,
                    reminder_text=reminder_text,
                )
            )
            return

        await message.answer(text.adding_3[lang])
        return

    await message.answer(text.adding_4[lang])
    await state.set_state(Form.waiting_for_message_time)


@dp.message(Form.waiting_for_message_time)
async def process_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    time_text = (message.text or "").strip()

    if time_text.startswith("/"):
        await state.clear()
        return

    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError:
        await message.answer(text.reminder_time_invalid[lang])
        return

    await state.update_data(time=time_text)
    await message.answer(text.reminder_time_received[lang].format(time_text=time_text))
    await state.set_state(Form.waiting_for_message_reminder)

@dp.message(Form.waiting_for_message_reminder)
async def process_reminder_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    reminder_text = (message.text or "").strip()

    if reminder_text.startswith("/"):
        await state.clear()
        return

    data = await state.get_data()
    time_text = data.get("time")

    rid = await add_reminder(db, user_id, time_text, reminder_text, rtype=0, pos=1)
    await state.update_data(reminder_id=rid)
    await message.answer(text.reminder_created[lang])
    await state.set_state(Form.waiting_for_message_type)

@dp.message(Form.waiting_for_message_type)
async def process_reminder_type(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    data = await state.get_data()
    rid = data.get("reminder_id")
    if not rid:
        await message.answer(text.session_not_found[lang])
        await state.clear()
        return

    value = (message.text or "").strip().lower()
    if value == "once":
        await update_reminder_type(db, rid, rtype=0, pos=1)
    elif value == "r":
        await update_reminder_type(db, rid, rtype=1, pos=1)
    else:
        await message.answer(text.reminder_type_invalid[lang])
        return

    await message.answer(text.reminder_type_saved[lang])
    await state.clear()

@dp.message(Command("delete"))
async def cmd_delete_reminder(message: types.Message, state: FSMContext):
    rows = await get_user_reminders(db, message.from_user.id)

    if not rows:
        await message.answer(text.no_reminders[lang])
        return

    lines = []
    for r in rows:
        rid, time_str, reminder_text, rtype = r[0], r[1], r[2], r[3]
        kind = "recurring" if rtype == 1 else "once"
        lines.append(f"id={rid} | {time_str} | {kind} | {reminder_text}")

    await message.answer("\n".join(lines))
    await message.answer(text.delete_choose_id[lang])
    await state.set_state(Form.waiting_for_message_delete_id)


@dp.message(Form.waiting_for_message_delete_id)
async def process_delete(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer(text.delete_send_number[lang])
        return

    try:
        id_text = int(message.text.strip())
    except ValueError:
        await message.answer(text.delete_send_number[lang])
        return

    try:
        await delete_reminder_from_db(db, id_text, message.from_user.id)
        await message.answer(text.delete_success[lang])
        await state.clear()
    except Exception as e:
        await message.answer(text.delete_error[lang])
        print(e)


@dp.message(Command("abc"))
async def cmd_abc(message: types.Message):
    rows = await get_user_reminders(db, message.from_user.id)

    if not rows:
        await message.answer(text.no_reminders[lang])
        return

    lines = []
    for r in rows:
        rid, time_str, reminder_text, rtype, pos = r[0], r[1], r[2], r[3], r[4]
        kind = "recurring" if rtype == 1 else "once"
        lines.append(f"id={rid} | {time_str} | {kind} | pos={pos} | {reminder_text}")

    await message.answer("\n".join(lines))


@dp.message(Command("set_lang"))
async def select_language(message: types.Message, state: FSMContext):
    lang = await get_language(db, message.from_user.id)
    await message.answer(text.set_lang1[lang])
    await state.set_state(Form.waiting_for_message_set_language)


@dp.message(Form.waiting_for_message_set_language)
async def process_set_lang(message: types.Message, state: FSMContext):
    new_lang = (message.text or "").strip().lower()

    if new_lang not in text.langs:
        current_lang = await get_language(db, message.from_user.id)
        await message.answer(text.set_lang2[current_lang])
        return

    try:
        await update_language(db, new_lang, message.from_user.id)
        await message.answer(text.set_lang3[new_lang])
        await state.clear()
    except Exception as e:
        await message.answer(text.set_lang4[new_lang])
        print(e)


@dp.message(Command("set_time"))
async def select__time_region(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    await message.answer(text.timezone_prompt[lang])
    await state.set_state(Form.waiting_for_message_set_time)


@dp.message(Form.waiting_for_message_set_time)
async def process_set_time(message: types.Message, state: FSMContext):
    time_text = (message.text or "").strip()
    user_id = message.from_user.id
    lang = await get_language(db, user_id)
    try:
        offset = int(time_text)
        if offset < -12 or offset > 12:
            raise ValueError

        await update_timezone_offset(db, message.from_user.id, offset)
        now = datetime.now(timezone(timedelta(hours=offset))).strftime("%H:%M")
        await message.answer(text.timezone_saved[lang].format(now=now))
        await state.clear()
    except ValueError:
        await message.answer(text.timezone_invalid[lang])


async def reminder_loop(db):
    logging.info("Reminder loop started")
    try:
        while True:
            users = await get_all_users(db)

            for user_id, offset in users:
                now_local = datetime.now(timezone.utc) + timedelta(hours=offset)
                current_time = now_local.strftime("%H:%M")
                current_date = now_local.strftime("%Y-%m-%d")

                rows = await get_due_reminders(db, user_id, current_time)

                for rid, _, _, reminder_text, rtype, pos, last_sent_date in rows:
                    try:
                        if rtype == 1 and last_sent_date == current_date:
                            continue

                        await bot.send_message(user_id, reminder_text)

                        if rtype == 0:
                            await mark_sent_once(db, rid)
                        else:
                            await mark_sent_recurring(db, rid, current_date)

                    except Exception:
                        logging.exception(f"Failed to send message to {user_id} (id={rid})")

            await asyncio.sleep(10)

    except asyncio.CancelledError:
        logging.info("Reminder loop cancelled")
        raise
async def main():
    global db
    db = await init_db()
    reminder_task = asyncio.create_task(reminder_loop(db))
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())