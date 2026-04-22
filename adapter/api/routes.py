import asyncio

from fastapi import APIRouter

from pipeline.poller import run_poll_cycle
from core.logging import logger
from db import repository

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/status")
async def status():
    """Текущее состояние адаптера: статистика БД и время последней синхронизации."""
    stats = await repository.get_stats()
    return {
        "status": "ok",
        "db_stats": stats,
    }


@router.post("/sync-now")
async def sync_now():
    """Запустить цикл поллинга вручную (не ждать следующего интервала)."""
    logger.info("Ручной запуск синхронизации через API")
    asyncio.create_task(run_poll_cycle())
    return {"status": "ok", "message": "Синхронизация запущена в фоне"}

@router.get("/debug/events")
async def debug_events(limit: int = 20, status: str = None):
    """Просмотр событий в БД (для отладки)."""
    import aiosqlite
    from core.config import settings

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row

        if status:
            query = "SELECT * FROM lms_events WHERE send_status = ? ORDER BY id DESC LIMIT ?"
            params = (status, limit)
        else:
            query = "SELECT * FROM lms_events ORDER BY id DESC LIMIT ?"
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            events = []
            for row in rows:
                d = dict(row)
                # raw_json может быть большим — обрезаем для читаемости
                if d.get("raw_json"):
                    d["raw_json"] = d["raw_json"][:200] + "..."
                events.append(d)

    return {
        "count": len(events),
        "events": events
    }
