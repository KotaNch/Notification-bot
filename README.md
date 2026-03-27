# Reminder Bot

A Telegram reminder bot built with Python, **aiogram**, and **SQLite**.  
It supports one-time reminders, recurring reminders, user-specific time zones, and language selection.

## Features

- Add reminders with a command or step-by-step flow
- Support for **one-time** and **recurring** reminders
- Per-user **language** settings (`ru` / `eng`)
- Per-user **timezone offset**
- Store data in **SQLite**
- Lightweight and easy to run locally

## Commands

- `/start` — show bot introduction and available commands
- `/add` — create a reminder step by step
- `/add <HH:MM>; <text>` — create a reminder in one message
- `/set_time` — set your timezone offset from UTC
- `/set_lang` — change language
- `/delete` — delete a reminder
- `/abc` — show your reminders for debugging

## Quick Start

Clone the repository, create a virtual environment, install dependencies, set your bot token, and run the bot:

```bash
git clone <your-repo-url>
cd telegramBotForNotifications
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export TOKEN="your_telegram_bot_token"
python main.py

