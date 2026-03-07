import aiosqlite
import os

DB_PATH = os.environ.get("REMINDER_DB", "reminders.db")

async def init_db():
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            time TEXT NOT NULL,
            text TEXT NOT NULL,
            type INTEGER NOT NULL DEFAULT 0,
            pos INTEGER NOT NULL DEFAULT 1,
            timezone_offset INTEGER
        );
    """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_time_pos ON reminders(time, pos);")
    await db.commit()
    return db

async def add_reminder(db, user_id: int, time_str: str, text: str, rtype: int = 0, pos: int = 1, tz_offset: int = None):
    query = """
    INSERT INTO reminders (user_id, time, text, type, pos, timezone_offset)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    await db.execute(query, (user_id, time_str, text, rtype, pos, tz_offset))
    await db.commit()
    cursor = await db.execute("SELECT last_insert_rowid()")
    row = await cursor.fetchone()
    return row[0] if row else None

async def get_due_reminders(db, time_str: str):
    q = "SELECT id, user_id, time, text, type, pos FROM reminders WHERE time = ? AND (pos = 1)"
    cur = await db.execute(q, (time_str,))
    rows = await cur.fetchall()
    return rows

async def mark_sent_once(db, reminder_id: int):
    await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    await db.commit()

async def mark_sent_recurring(db, reminder_id: int):
    await db.execute("UPDATE reminders SET pos = 0 WHERE id = ?", (reminder_id,))
    await db.commit()

async def reset_pos_all(db):
    await db.execute("UPDATE reminders SET pos = 1")
    await db.commit()

async def update_reminder_type(db, reminder_id: int, rtype: int, pos: int):
    await db.execute("UPDATE reminders SET type = ?, pos = ? WHERE id = ?", (rtype, pos, reminder_id))
    await db.commit()

async def get_user_reminders(db, user_id: int):
    cur = await db.execute("SELECT id, time, text, type, pos FROM reminders WHERE user_id = ? ORDER BY time", (user_id,))
    rows = await cur.fetchall()
    return rows