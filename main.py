import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("Environment variable TOKEN is not set")

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class Form(StatesGroup):
    waiting_for_message_time = State()
    waiting_for_message_reminder = State()


# список напоминаний в памяти (каждый элемент — dict: id, user_id, time, text)
users = []
next_id = 0  # следующий id напоминания


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в бот для уведомлений! sdfasjdfklasdfh\n"
        "Команды:\n"
        "/add — пошаговое добавление\n"
        "/add <ЧЧ:ММ>; <текст> — добавить одним сообщением"
    )


@dp.message(Command("add"))
async def add_notification(message: types.Message, command: CommandObject, state: FSMContext):
    """
    Поддерживаем два варианта:
    1) /add <HH:MM>; <text> — всё в одной строке (разбираем command.args)
    2) /add — запускаем пошаговую процедуру: сначала время, затем текст
    """
    global next_id

    if command.args:
        # ожидаем формат "HH:MM; text"
        parts = command.args.split(";", 1)
        if len(parts) == 2:
            time_str = parts[0].strip()
            text = parts[1].strip()
            # валидация времени
            try:
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                await message.answer("Неправильный формат времени. Используйте ЧЧ:ММ.")
                return
            users.append({"id": next_id, "user_id": message.from_user.id, "time": time_str, "text": text})
            next_id += 1
            await message.answer(f"Напоминание добавлено: {time_str} — {text}")
            return

        # если аргументы есть, но не в ожидаемом формате
        await message.answer("Параметры не распознаны. Используйте: /add <ЧЧ:ММ>; <текст> или просто /add")
        return

    # пошаговый режим
    await message.answer("Отправьте время в формате ЧЧ:ММ")
    await state.set_state(Form.waiting_for_message_time)


@dp.message(Form.waiting_for_message_time)
async def process_time(message: types.Message, state: FSMContext):
    time_text = message.text.strip()
    # проверка формата
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
    await state.clear()  # выходим из состояния


async def reminder_loop():
    logging.info("Reminder loop started")
    while True:
        now = datetime.now().strftime("%H:%M")
        # итерируем по копии списка, чтобы безопасно удалять элементы
        for reminder in users[:]:
            if reminder["time"] == now:
                try:
                    await bot.send_message(reminder["user_id"], reminder["text"])
                    logging.info(f"Message sent to {reminder['user_id']} (id={reminder['id']})")
                    users.remove(reminder)
                except Exception:
                    logging.exception(f"Failed to send message to {reminder['user_id']}")
        # пауза — 10 секунд (можно увеличить до 30 или 60)
        await asyncio.sleep(10)


async def main():
    # запускаем цикл отправки напоминаний и polling
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
