import aiosqlite

from core.config import settings


async def get_connection() -> aiosqlite.Connection:
    """Открывает соединение с row_factory для удобного доступа по имени."""
    conn = await aiosqlite.connect(settings.db_path)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    """Создаёт все таблицы при старте."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript("""
            -- Состояние поллинга (ключ-значение)
            CREATE TABLE IF NOT EXISTS sync_state (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- Сырые данные о прогрессе пользователей из LMS.
            -- Храним каждый submission/quiz-attempt как отдельную строку.
            CREATE TABLE IF NOT EXISTS lms_events (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id            TEXT    NOT NULL UNIQUE,  -- наш составной ключ
                lms_user_id         INTEGER NOT NULL,
                task_external_id    TEXT    NOT NULL,
                task_type           TEXT    NOT NULL,         -- "code" | "test"
                passed              INTEGER NOT NULL DEFAULT 0,
                total               INTEGER NOT NULL DEFAULT 0,
                attempts            INTEGER NOT NULL DEFAULT 1,
                duration_seconds    INTEGER NOT NULL DEFAULT 0,
                code_submitted      TEXT,                     -- только для code-задач
                raw_json            TEXT,                     -- полный JSON строки из LMS (для отладки)
                fetched_at          TIMESTAMP NOT NULL,
                -- Статус отправки в наш webhook
                send_status         TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | failed
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