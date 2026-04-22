import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from core.config import settings
from core.logging import logger


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


async def upsert_lms_event(
    *,
    event_id: str,
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
    Вставляет новое событие.
    Возвращает True если событие новое, False — если уже было.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT id FROM lms_events WHERE event_id = ?", (event_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            return False  # Уже есть — не дублируем

        await db.execute(
            """
            INSERT INTO lms_events
                (event_id, lms_user_id, task_external_id, task_type,
                 passed, total, attempts, duration_seconds,
                 code_submitted, raw_json, fetched_at, send_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                event_id,
                lms_user_id,
                task_external_id,
                task_type,
                passed,
                total,
                attempts,
                duration_seconds,
                code_submitted,
                json.dumps(raw_data, ensure_ascii=False),
                fetched_at.isoformat(),
            ),
        )
        await db.commit()
        return True


async def get_pending_events(limit: int = 100) -> list[dict]:
    """Возвращает события, которые ещё не отправлены."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM lms_events
            WHERE send_status = 'pending'
            ORDER BY fetched_at ASC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def mark_event_sent(event_id: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            UPDATE lms_events
            SET send_status = 'sent',
                send_attempts = send_attempts + 1,
                sent_at = ?,
                last_error = NULL
            WHERE event_id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), event_id),
        )
        await db.commit()


async def mark_event_failed(event_id: str, error: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            UPDATE lms_events
            SET send_status = 'failed',
                send_attempts = send_attempts + 1,
                last_error = ?
            WHERE event_id = ?
            """,
            (error[:1000], event_id),  # обрезаем, чтобы не переполнить
        )
        await db.commit()


async def get_stats() -> dict:
    """Статистика для /status endpoint."""
    async with aiosqlite.connect(settings.db_path) as db:
        stats = {}
        for status in ("pending", "sent", "failed"):
            async with db.execute(
                "SELECT COUNT(*) FROM lms_events WHERE send_status = ?", (status,)
            ) as cur:
                row = await cur.fetchone()
                stats[status] = row[0] if row else 0

        async with db.execute(
            "SELECT value FROM sync_state WHERE key = 'last_sync'"
        ) as cur:
            row = await cur.fetchone()
            stats["last_sync"] = row[0] if row else None

        return stats