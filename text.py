languages = {"eng": 1, "ru": 0}
langs = ["eng", "ru"]

start_message = {
    "ru": (
        "Добро пожаловать в бот для уведомлений!\n"
        "Команды:\n"
        "/add — пошаговое добавление\n"
        "/add <ЧЧ:ММ>; <текст> — добавить одним сообщением\n"
        "/set_time — установить часовой пояс (смещение в часах от UTC)\n"
        "/set_lang — изменить язык\n"
        "/delete — удалить напоминание\n"
        "/abc — показать ваши напоминания (отладка)\n"
    ),
    "eng": (
        "Welcome to the reminder bot!\n"
        "Commands:\n"
        "/add — step-by-step adding\n"
        "/add <HH:MM>; <text> — add in one message\n"
        "/set_time — set the time zone (offset in hours from UTC)\n"
        "/set_lang — change language\n"
        "/delete — delete a reminder\n"
        "/abc — show your reminders (debugging)\n"
    ),
}

adding_1 = {
    "ru": "Неправильный формат времени. Используйте ЧЧ:ММ.",
    "eng": "Invalid time format. Use HH:MM.",
}

adding_2 = {
    "ru": (
        "Напоминание добавлено (id={rid}): {time_str} — {reminder_text}\n"
        "Чтобы сделать его повторяющимся, используйте пошаговый /add или отредактируйте тип."
    ),
    "eng": (
        "Reminder added (id={rid}): {time_str} — {reminder_text}\n"
        "To make it repeating, use stepwise /add or edit the type."
    ),
}

adding_3 = {
    "ru": "Параметры не распознаны. Используйте: /add <ЧЧ:ММ>; <текст> или просто /add",
    "eng": "The parameters are not recognized. Use: /add <HH:MM>; <text> or simply /add",
}

adding_4 = {
    "ru": "Отправьте время в формате ЧЧ:ММ",
    "eng": "Send the time in HH:MM format",
}

reminder_time_invalid = {
    "ru": "Неправильный формат. Укажите время в формате ЧЧ:ММ (например, 17:30).",
    "eng": "Invalid format. Send time in HH:MM format (for example, 17:30).",
}

reminder_time_received = {
    "ru": "Принято: {time_text}. Теперь отправьте текст напоминания:",
    "eng": "Received: {time_text}. Now send the reminder text:",
}

reminder_created = {
    "ru": 'Напоминание создано. Теперь отправьте тип сообщения: "once" или "r" (recurring).',
    "eng": 'Reminder created. Now send the message type: "once" or "r" (recurring).',
}

reminder_type_invalid = {
    "ru": 'Неверный тип. Отправьте "once" или "r".',
    "eng": 'Invalid type. Send "once" or "r".',
}

reminder_type_saved = {
    "ru": "Тип напоминания сохранён.",
    "eng": "Reminder type saved.",
}

session_not_found = {
    "ru": "Не найдено напоминание в сессии. Начните заново с /add.",
    "eng": "No reminder found in session. Start again with /add.",
}

no_reminders = {
    "ru": "У вас нет напоминаний.",
    "eng": "You have no reminders.",
}

delete_choose_id = {
    "ru": "Введите id сообщения, которое хотите удалить",
    "eng": "Enter the id of the reminder you want to delete",
}

delete_send_number = {
    "ru": "Отправь число",
    "eng": "Send a number",
}

delete_success = {
    "ru": "Сообщение удалено!",
    "eng": "Reminder deleted!",
}

delete_error = {
    "ru": "Ошибка удаления",
    "eng": "Deletion error",
}

set_lang1 = {
    "ru": "Введите нужный вам язык: русский (ru) или английский (eng)",
    "eng": "Enter the language you need: Russian (ru) or English (eng)",
}

set_lang2 = {
    "ru": "Вашего языка нет или вы его написали не правильно",
    "eng": "Your language doesn't exist or you wrote it incorrectly.",
}

set_lang3 = {
    "ru": "Язык успешно изменен",
    "eng": "Language successfully changed",
}

set_lang4 = {
    "ru": "Ошибка при попытке изменить язык",
    "eng": "Error while trying to change language",
}

timezone_prompt = {
    "ru": "Введите часовой пояс от -12 до 12 (целое число часов, например 3 или -5)",
    "eng": "Enter the timezone from -12 to 12 (whole hours, for example 3 or -5)",
}

timezone_saved = {
    "ru": "Часовой пояс сохранён.\nВаше текущее время: {now}",
    "eng": "Timezone saved.\nYour current time: {now}",
}

timezone_invalid = {
    "ru": "Неверный формат. Введите целое число от -12 до 12 (например 5 или -3).",
    "eng": "Invalid format. Enter an integer from -12 to 12 (for example 5 or -3).",
}

reminder_kind_once = {
    "ru": "одноразовое",
    "eng": "once",
}

reminder_kind_recurring = {
    "ru": "повторяющееся",
    "eng": "recurring",
}

reminder_kind = {
    "ru": {0: "одноразовое", 1: "повторяющееся"},
    "eng": {0: "once", 1: "recurring"},
}