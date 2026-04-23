import aiosqlite

from core.config import settings


async def get_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(settings.db_path)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    """Создаёт все таблицы при старте."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS sync_state (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lms_events (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id            TEXT    NOT NULL UNIQUE,
                lms_user_id         INTEGER NOT NULL,
                task_external_id    TEXT    NOT NULL,
                task_type           TEXT    NOT NULL,
                vacancy_id          TEXT    NOT NULL,
                passed              INTEGER NOT NULL DEFAULT 0,
                total               INTEGER NOT NULL DEFAULT 0,
                attempts            INTEGER NOT NULL DEFAULT 1,
                duration_seconds    INTEGER NOT NULL DEFAULT 0,
                code_submitted      TEXT,
                raw_json            TEXT,
                fetched_at          TIMESTAMP NOT NULL,
                send_status         TEXT NOT NULL DEFAULT 'pending',
                send_attempts       INTEGER NOT NULL DEFAULT 0,
                last_error          TEXT,
                sent_at             TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_lms_events_send_status
                ON lms_events (send_status);

            CREATE INDEX IF NOT EXISTS idx_lms_events_lms_user_id
                ON lms_events (lms_user_id);
        """)
        await db.commit()