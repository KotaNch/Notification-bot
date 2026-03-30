import aiosqlite
import os

DB_PATH = os.environ.get("REMINDER_DB", "reminders.db")


async def init_db():
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT NOT NULL DEFAULT 'eng',
            timezone_offset INTEGER NOT NULL DEFAULT 0
        );
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT,                       -- новое поле
            time TEXT NOT NULL,
            text TEXT NOT NULL,
            type INTEGER NOT NULL DEFAULT 0,
            pos INTEGER NOT NULL DEFAULT 1,
            last_sent_date TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)


    cur = await db.execute("PRAGMA table_info(reminders)")
    cols = {row[1] for row in await cur.fetchall()}
    if "date" not in cols:
        await db.execute("ALTER TABLE reminders ADD COLUMN date TEXT")
    if "last_sent_date" not in cols:
        await db.execute("ALTER TABLE reminders ADD COLUMN last_sent_date TEXT NOT NULL DEFAULT ''")

    await db.execute("CREATE INDEX IF NOT EXISTS idx_time_pos ON reminders(time, pos);")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON reminders(user_id);")
    await db.commit()
    return db


async def ensure_user(db, user_id: int):
    await db.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    await db.commit()


async def add_reminder(db, user_id: int, time_str: str, text: str, date: str | None = None, rtype: int = 0):
    await ensure_user(db, user_id)

    query = """
    INSERT INTO reminders (user_id, date, time, text, type, pos, last_sent_date)
    VALUES (?, ?, ?, ?, ?, ?, '')
    """
    await db.execute(query, (user_id, date, time_str, text, rtype, 1))
    await db.commit()

    cursor = await db.execute("SELECT last_insert_rowid()")
    row = await cursor.fetchone()
    return row[0] if row else None


async def delete_reminder_from_db(db, reminder_id: int, user_id: int | None = None):
    if user_id is None:
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    else:
        await db.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id)
        )
    await db.commit()


async def get_due_reminders(db, user_id: int, time_str: str):
    q = """
    SELECT id, user_id, time, text, type, pos, last_sent_date
    FROM reminders
    WHERE user_id = ? AND time = ?
    """
    cur = await db.execute(q, (user_id, time_str))
    return await cur.fetchall()


async def get_all_users(db):
    cur = await db.execute("SELECT user_id, timezone_offset FROM users")
    return await cur.fetchall()


async def get_language(db, user_id: int):
    await ensure_user(db, user_id)
    cur = await db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return row[0] if row else "eng"


async def update_language(db, language: str, user_id: int):
    await ensure_user(db, user_id)
    await db.execute(
        "UPDATE users SET lang = ? WHERE user_id = ?",
        (language, user_id)
    )
    await db.commit()


async def get_timezone_offset(db, user_id: int):
    await ensure_user(db, user_id)
    cur = await db.execute("SELECT timezone_offset FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return row[0] if row else 0


async def update_timezone_offset(db, user_id: int, offset: int):
    await ensure_user(db, user_id)
    await db.execute(
        "UPDATE users SET timezone_offset = ? WHERE user_id = ?",
        (offset, user_id)
    )
    await db.commit()


async def mark_sent_once(db, reminder_id: int):
    await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    await db.commit()


async def mark_sent_recurring(db, reminder_id: int, sent_date: str):
    await db.execute(
        "UPDATE reminders SET last_sent_date = ? WHERE id = ?",
        (sent_date, reminder_id)
    )
    await db.commit()


async def update_reminder_type(db, reminder_id: int, rtype: int, pos: int):
    await db.execute(
        "UPDATE reminders SET type = ?, pos = ? WHERE id = ?",
        (rtype, pos, reminder_id)
    )
    await db.commit()


async def get_user_reminders(db, user_id: int):
    cur = await db.execute(
        "SELECT id, date, time, text, type, pos, last_sent_date FROM reminders WHERE user_id = ? ORDER BY time",
        (user_id,)
    )
    return await cur.fetchall()