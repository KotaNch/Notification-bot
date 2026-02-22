import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("Environment variable TOKEN is not set")

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_message_time = State()
    waiting_for_message_reminder = State()

# список напоминаний в памяти
region = ['Kazakhstan','Astana']
users = []
next_id = 0  # следующий id напоминания

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в бот для уведомлений!\n"
        "Команды:\n"
        "/add — пошаговое добавление\n"
        "/add <ЧЧ:ММ>; <текст> — добавить одним сообщением"
    )

@dp.message(Command("add"))
async def add_notification(message: types.Message, state: FSMContext):
    """
    Поддерживаем два варианта:
    1) /add <HH:MM>; <text> — всё в одной строке
    2) /add — пошаговый режим (время -> текст)
    """
    global next_id

    # безопасно извлекаем аргументы из message.text (без зависимости от CommandObject)
    text = message.text or ""
    # Split after the command and optional bot username. e.g. "/add 12:00; test"
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
            users.append({"id": next_id, "user_id": message.from_user.id, "time": time_str, "text": reminder_text})
            next_id += 1
            await message.answer(f"Напоминание добавлено: {time_str} — {reminder_text}")
            return

        await message.answer("Параметры не распознаны. Используйте: /add <ЧЧ:ММ>; <текст> или просто /add")
        return

    # пошаговый режим
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
async def process_msg2(message: types.Message, state: FSMContext):
    global next_id
    data = await state.get_data()
    time_text = data.get("time")
    text = message.text.strip()

    users.append({"id": next_id, "user_id": message.from_user.id, "time": time_text, "text": text})
    next_id += 1

    await message.answer(f"Напоминание добавлено: {time_text} — {text}")
    await state.clear()

async def reminder_loop():
    logging.info("Reminder loop started")
    try:
        while True:
            now = datetime.now(ZoneInfo(region[0],'/',region[1])).strftime("%H:%M")
            for reminder in users[:]:
                if reminder["time"] == now:
                    try:
                        await bot.send_message(reminder["user_id"], reminder["text"])
                        logging.info(f"Message sent to {reminder['user_id']} (id={reminder['id']})")
                        users.remove(reminder)
                    except Exception:
                        logging.exception(f"Failed to send message to {reminder['user_id']}")
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        logging.info("Reminder loop cancelled")
        raise

@dp.message(Command("abc"))
async def cmd_start(message: types.Message):
    await message.answer(
        users
    )

async def main():
    reminder_task = asyncio.create_task(reminder_loop())
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())