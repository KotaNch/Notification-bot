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
    waiting_for_date = State()          
    waiting_for_time = State()           
    waiting_for_text = State()
    waiting_for_type = State()           
    waiting_for_delete_id = State()
    waiting_for_set_language = State()
    waiting_for_set_time = State()

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
        date_str = None
        time_str = None
        reminder_text = None

        parts = args.split(";")
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) == 2:
            time_str = parts[0]
            reminder_text = parts[1]
        elif len(parts) == 3:
            date_str = parts[0]
            time_str = parts[1]
            reminder_text = parts[2]
        else:
            space_parts = args.split(maxsplit=2)
            if len(space_parts) == 2:
                time_str = space_parts[0]
                reminder_text = space_parts[1]
            elif len(space_parts) == 3:
                date_time_str = f"{space_parts[0]} {space_parts[1]}"
                reminder_text = space_parts[2]
                try:
                    dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M")
                except ValueError:
                    await message.answer(text.adding_1[lang])
                    return
            else:
                await message.answer(text.adding_3[lang])
                return

        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await message.answer(text.adding_1[lang])
            return

        rtype = 0 if date_str else 1

        rid = await add_reminder(db, user_id, time_str, reminder_text, date=date_str, rtype=rtype)
        answer = text.adding_2[lang].format(
            rid=rid,
            time_str=time_str,
            reminder_text=reminder_text,
        )
        if date_str:
            answer += f" (одноразовое на {date_str})" if lang == "ru" else f" (one-time on {date_str})"
        await message.answer(answer)
        return

    await message.answer(text.ask_date[lang])
    await state.set_state(Form.waiting_for_date)
@dp.message(Form.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    date_text = (message.text or "").strip().lower()


    if date_text in ("-", "skip", "пропустить"):
        await state.update_data(date=None)
        await message.answer(text.reminder_date_skip[lang])
        await state.set_state(Form.waiting_for_time)
        return
    try:
        dt = datetime.strptime(date_text, "%Y-%m-%d")
        
        if dt.date() < datetime.now().date():
            await message.answer(text.reminder_date_past[lang])
            return
        await state.update_data(date=dt.strftime("%Y-%m-%d"))
        await message.answer(text.reminder_date_received[lang].format(date=date_text))
        await state.set_state(Form.waiting_for_time)
    except ValueError:
        await message.answer(text.reminder_date_invalid[lang])
    

@dp.message(Form.waiting_for_time)
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
    await state.set_state(Form.waiting_for_text)

@dp.message(Form.waiting_for_text)
async def process_reminder_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    reminder_text = (message.text or "").strip()

    if reminder_text.startswith("/"):
        await state.clear()
        return

    data = await state.get_data()
    date = data.get("date")
    time_text = data.get("time")

    if date:
        # Если дата указана, тип once
        rtype = 0
        rid = await add_reminder(db, user_id, time_text, reminder_text, date=date, rtype=rtype)
        await message.answer(
            text.reminder_created[lang] +
            (f" (одноразовое на {date})" if lang == "ru" else f" (one-time on {date})")
        )
        await state.clear()
    else:
        # Сохраняем текст и спрашиваем тип
        await state.update_data(text=reminder_text)
        await message.answer(text.reminder_type_prompt[lang])
        await state.set_state(Form.waiting_for_type)

@dp.message(Form.waiting_for_type)
async def process_reminder_type(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(db, user_id)

    value = (message.text or "").strip().lower()
    if value == "once":
        rtype = 0
    elif value in ("recurring", "r"):
        rtype = 1
    else:
        await message.answer(text.reminder_type_invalid[lang])
        return

    data = await state.get_data()
    date = data.get("date") 
    time_text = data.get("time")
    reminder_text = data.get("text")

    rid = await add_reminder(db, user_id, time_text, reminder_text, date=date, rtype=rtype)
    await message.answer(text.reminder_created[lang])
    await state.clear()

@dp.message(Command("delete"))
async def cmd_delete_reminder(message: types.Message, state: FSMContext):
    lang = await get_language(db, message.from_user.id)
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
    await state.set_state(Form.waiting_for_delete_id)


@dp.message(Form.waiting_for_delete_id)
async def process_delete(message: types.Message, state: FSMContext):
    lang = await get_language(db, message.from_user.id)
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

# It only for tests and something like this...
# @dp.message(Command("abc"))
# async def cmd_abc(message: types.Message):
#     lang = await get_language(db, message.from_user.id)
#     rows = await get_user_reminders(db, message.from_user.id)

#     if not rows:
#         await message.answer(text.no_reminders[lang])
#         return

#     lines = []
#     for r in rows:
#         rid, date, time_str, reminder_text, rtype, pos, last_sent = r
#         kind = "recurring" if rtype == 1 else "once"
#         date_info = f" date={date}" if date else ""
#         lines.append(f"id={rid} | {time_str} | {kind} | pos={pos} | {reminder_text}{date_info}")

#     await message.answer("\n".join(lines))

@dp.message(Command("set_lang"))
async def select_language(message: types.Message, state: FSMContext):
    lang = await get_language(db, message.from_user.id)
    await message.answer(text.set_lang1[lang])
    await state.set_state(Form.waiting_for_set_language)


@dp.message(Form.waiting_for_set_language)
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
    await state.set_state(Form.waiting_for_set_time)


@dp.message(Form.waiting_for_set_time)
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

                rows = await db.execute("""
                SELECT id, date, time, text, type, last_sent_date
                FROM reminders
                WHERE user_id = ? AND time = ?
                """, (user_id, current_time))

                rows = await rows.fetchall()
                for rid, date, _, reminder_text, rtype, last_sent_date in rows:
                    if date is not None and date != current_date:
                        continue
                    if rtype == 1 and last_sent_date == current_date:
                        continue

                    await bot.send_message(user_id, reminder_text)

    
                    if date is not None or rtype == 0:
                        await mark_sent_once(db, rid)
                    else:
                        await mark_sent_recurring(db, rid, current_date)

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