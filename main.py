import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from db import init_db, add_reminder, get_due_reminders, mark_sent_once, mark_sent_recurring, reset_pos_all, update_reminder_type, get_user_reminders

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

dtime = 5          
db = None        

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в бот для уведомлений!\n"
        "Команды:\n"
        "/add — пошаговое добавление\n"
        "/add <ЧЧ:ММ>; <текст> — добавить одним сообщением\n"
        "/set_time — установить часовой пояс (смещение в часах от UTC)\n"
        "/abc — показать ваши напоминания (отладка)\n"
    )

@dp.message(Command("add"))
async def add_notification(message: types.Message, state: FSMContext):
    text = message.text or ""
    parts_after_cmd = text.split(None, 1)
    args = parts_after_cmd[1].strip() if len(parts_after_cmd) > 1 else ""

    if args:
        parts = args.split(";", 1)
        if len(parts) == 2:
            time_str = parts[0].strip()
            reminder_text = parts[1].strip()
            try:
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                await message.answer("Неправильный формат времени. Используйте ЧЧ:ММ.")
                return
          
            rid = await add_reminder(db, message.from_user.id, time_str, reminder_text, rtype=0, pos=1)
            await message.answer(f"Напоминание добавлено (id={rid}): {time_str} — {reminder_text}\nЧтобы сделать его повторяющимся, используйте пошаговый /add или отредактируйте тип.")
            return

        await message.answer("Параметры не распознаны. Используйте: /add <ЧЧ:ММ>; <текст> или просто /add")
        return

    await message.answer("Отправьте время в формате ЧЧ:ММ")
    await state.set_state(Form.waiting_for_message_time)

@dp.message(Form.waiting_for_message_time)
async def process_time(message: types.Message, state: FSMContext):
    time_text = message.text.strip()
    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError:
        await message.answer("Неправильный формат. Укажите время в формате ЧЧ:ММ (например, 17:30).")
        return

    await state.update_data(time=time_text)
    await message.answer(f"Принято: {time_text}. Теперь отправьте текст напоминания:")
    await state.set_state(Form.waiting_for_message_reminder)

@dp.message(Form.waiting_for_message_reminder)
async def process_reminder_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    time_text = data.get("time")
    text = message.text.strip()


    rid = await add_reminder(db, message.from_user.id, time_text, text, rtype=0, pos=1)
    await state.update_data(reminder_id=rid)
    await message.answer('Напоминание создано. Теперь отправьте тип сообщения: "once" или "r" (recurring).')
    await state.set_state(Form.waiting_for_message_type)

@dp.message(Form.waiting_for_message_type)
async def process_reminder_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    rid = data.get("reminder_id")
    if not rid:
        await message.answer("Не найдено напоминание в сессии. Начните заново с /add.")
        await state.clear()
        return

    text = message.text.strip().lower()
    if text == 'once':
        await update_reminder_type(db, rid, rtype=0, pos=1)
    elif text == 'r':
        await update_reminder_type(db, rid, rtype=1, pos=1)
    else:
        await message.answer('Неверный тип. Отправьте "once" или "r".')
        return

    await message.answer("Тип напоминания сохранён.")
    await state.clear()

@dp.message(Command("abc"))
async def cmd_abc(message: types.Message):
    rows = await get_user_reminders(db, message.from_user.id)
  
    if not rows:
        await message.answer("У вас нет напоминаний.")
        return
    lines = []
    for r in rows:
        rid, time_str, text, rtype, pos = r[0], r[1], r[2], r[3], r[4]
        kind = "recurring" if rtype == 1 else "once"
        lines.append(f"id={rid} | {time_str} | {kind} | pos={pos} | {text}")
    await message.answer("\n".join(lines))

@dp.message(Command("set_time"))
async def select__time_region(message:types.Message,state: FSMContext):
    await message.answer(f"Введите часовой пояс от -12 до 12 (целое число часов, например 3 или -5)")
    await state.set_state(Form.waiting_for_message_set_time)

@dp.message(Form.waiting_for_message_set_time)
async def process_set_time(message: types.Message, state: FSMContext):
    time_text = message.text.strip()
    try:
        global dtime
        dtime = int(time_text)
        now = datetime.now(timezone(timedelta(hours=dtime))).strftime("%H:%M")
        await message.answer(f"Часовой пояс сохранён.\nВаше текущее время: {now}")
        await state.clear()
    except Exception:
        await message.answer("Неверный формат. Введите целое число от -12 до 12 (например 5 или -3).")


async def reminder_loop(db):
    logging.info("Reminder loop started")
    try:
        while True:
            now = datetime.now(timezone(timedelta(hours=dtime))).strftime("%H:%M")
            rows = await get_due_reminders(db, now)
            for row in rows:
                rid, user_id, _, text, rtype, pos = row
                try:
                    await bot.send_message(user_id, text)
                    logging.info(f"Message sent to {user_id} (id={rid})")
                    if rtype == 0:
                        await mark_sent_once(db, rid)
                    else:
                        await mark_sent_recurring(db, rid)
                except Exception:
                    logging.exception(f"Failed to send message to {user_id} (id={rid})")
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        logging.info("Reminder loop cancelled")
        raise

async def zero_loop(db):
    try:
        while True:
            now = datetime.now(timezone(timedelta(hours=dtime))).strftime("%H:%M")
            if now == "00:00":
                await reset_pos_all(db)
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        logging.info("zero loop cancelled")
        raise

async def main():
    global db
    db = await init_db()
    reminder_task = asyncio.create_task(reminder_loop(db))
    zero_task = asyncio.create_task(zero_loop(db))
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        zero_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        try:
            await zero_task
        except asyncio.CancelledError:
            pass
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())