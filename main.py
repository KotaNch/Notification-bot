import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject   # <-- added CommandObject

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get('TOKEN')
bot = Bot(TOKEN)
dp = Dispatcher()


users = []          
next_id = 0         

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в бот для уведомлений!\n"
        "Возможные команды:\n"
        "/add <время(ЧЧ:ММ)>; <сообщение> - добавляет напоминание"
    )

@dp.message(Command("add"))
async def add_notification(message: types.Message, command: CommandObject):
    global next_id
    user_id = message.from_user.id

    args = command.args
    if args is None or ";" not in args:
        await message.answer("Ошибка: используйте формат /add ЧЧ:ММ; сообщение")
        return

    try:
        user_time, user_message = args.split(";", 1)  
        user_time = user_time.strip()
        user_message = user_message.strip()

       
        datetime.strptime(user_time, "%H:%M")

        
        reminder = {
            "id": next_id,
            "user_id": user_id,
            "time": user_time,
            "text": user_message
        }
        users.append(reminder)
        next_id += 1

        await message.answer("Уведомление успешно добавлено")
        logging.info(f"Users: {users}")
    except ValueError:
        await message.answer("Ошибка: время должно быть в формате ЧЧ:ММ (например, 19:39)")
    except Exception as e:
        await message.answer("Произошла ошибка при добавлении")
        logging.error(f"Add error: {e}")

async def reminder_loop(bot: Bot):
    logging.info("Reminder loop started")
    while True:
        now = datetime.now().strftime("%H:%M")
        
        for reminder in users[:]:
            if now == reminder["time"]:
                try:
                    await bot.send_message(reminder["user_id"], reminder["text"])
                    logging.info(f"Message sent to {reminder['user_id']}")
                    users.remove(reminder)   
                except Exception as e:
                    logging.error(f"Send error: {e}")
        await asyncio.sleep(10)   

async def main():
    asyncio.create_task(reminder_loop(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())