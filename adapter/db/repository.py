import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from core.config import settings


async def get_last_sync_time() -> Optional[datetime]:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT value FROM sync_state WHERE key = 'last_sync'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
    return None


async def set_last_sync_time(dt: datetime) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES ('last_sync', ?)",
            (dt.isoformat(),),
        )
        await db.commit()


async def upsert_event(
    *,
    event_id: str,
    course_id: int,
    vacancy_id: str,
    lms_user_id: int,
    task_external_id: str,
    task_type: str,
    passed: int,
    total: int,
    attempts: int,
    duration_seconds: int,
    code_submitted: Optional[str],
    raw_data: dict,
    fetched_at: datetime,
) -> bool:
    """
    Вставляет новое событие в outbox.
    Возвращает True если событие новое, False — если уже было.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT id FROM events_outbox WHERE event_id = ?", (event_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            return False

        await db.execute(
            """
            INSERT INTO events_outbox
                (event_id, course_id, vacancy_id, lms_user_id,
                 task_external_id, task_type,
                 passed, total, attempts, duration_seconds,
                 code_submitted, raw_json, fetched_at, send_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                event_id, course_id, vacancy_id, lms_user_id,
                task_external_id, task_type,
                passed, total, attempts, duration_seconds,
                code_submitted,
                json.dumps(raw_data, ensure_ascii=False),
                fetched_at.isoformat(),
            ),
        )
        await db.commit()
        return True


async def get_pending_events(limit: int = 200) -> list[dict]:
    """Возвращает pending события для отправки."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM events_outbox
            WHERE send_status = 'pending'
            ORDER BY fetched_at ASC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_dlq_events(limit: int = 100) -> list[dict]:
    """Возвращает события в DLQ."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM events_outbox
            WHERE send_status = 'dlq'
            ORDER BY fetched_at ASC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def requeue_dlq_events() -> int:
    """
    Переводит все dlq события обратно в pending.
    Возвращает количество переведённых событий.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            """
            UPDATE events_outbox
            SET send_status = 'pending',
                last_error = NULL
            WHERE send_status = 'dlq'
            """
        )
        await db.commit()
        return cursor.rowcount


async def mark_event_sent(event_id: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            UPDATE events_outbox
            SET send_status = 'sent',
                send_attempts = send_attempts + 1,
                sent_at = ?,
                last_error = NULL
            WHERE event_id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), event_id),
        )
        await db.commit()


async def mark_event_failed(event_id: str, error: str, send_attempts: int) -> None:
    """
    Помечает событие как failed или dlq в зависимости от числа попыток.
    """
    new_status = (
        "dlq"
        if send_attempts >= settings.webhook_max_attempts
        else "failed"
    )
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            UPDATE events_outbox
            SET send_status = ?,
                send_attempts = send_attempts + 1,
                last_error = ?
            WHERE event_id = ?
            """,
            (new_status, error[:1000], event_id),
        )
        await db.commit()


async def requeue_failed_events() -> int:
    """
    Переводит failed события обратно в pending для retry.
    Если send_attempts >= webhook_max_attempts → переводит в dlq.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        # Сначала переводим в dlq те что исчерпали попытки
        await db.execute(
            """
            UPDATE events_outbox
            SET send_status = 'dlq'
            WHERE send_status = 'failed'
              AND send_attempts >= ?
            """,
            (settings.webhook_max_attempts,),
        )

        # Остальные failed → pending
        cursor = await db.execute(
            """
            UPDATE events_outbox
            SET send_status = 'pending',
                last_error = NULL
            WHERE send_status = 'failed'
              AND send_attempts < ?
            """,
            (settings.webhook_max_attempts,),
        )
        await db.commit()
        return cursor.rowcount


async def get_stats() -> dict:
    """Статистика для /api/status."""
    async with aiosqlite.connect(settings.db_path) as db:
        stats = {}
        for status in ("pending", "sent", "failed", "dlq"):
            async with db.execute(
                "SELECT COUNT(*) FROM events_outbox WHERE send_status = ?",
                (status,),
            ) as cur:
                row = await cur.fetchone()
                stats[status] = row[0] if row else 0

        async with db.execute(
            "SELECT value FROM sync_state WHERE key = 'last_sync'"
        ) as cur:
            row = await cur.fetchone()
            stats["last_sync"] = row[0] if row else None

        return stats