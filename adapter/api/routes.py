import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from pipeline.poller import run_poll_cycle
from pipeline.external_tasks import get_external_tasks
from core.logging import logger
from db import repository

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/status")
async def status():
    """Статистика адаптера."""
    stats = await repository.get_stats()
    return {"status": "ok", "db_stats": stats}


@router.post("/sync-now")
async def sync_now():
    """Форс-запуск цикла поллинга."""
    logger.info("Ручной запуск синхронизации")
    asyncio.create_task(run_poll_cycle())
    return {"status": "ok", "message": "Синхронизация запущена в фоне"}


@router.get("/dlq")
async def get_dlq(limit: int = Query(default=100, le=500)):
    """Список событий в DLQ."""
    events = await repository.get_dlq_events(limit=limit)
    return {"count": len(events), "events": events}


@router.post("/dlq/requeue")
async def requeue_dlq():
    """Вернуть DLQ события в pending для повторной отправки."""
    count = await repository.requeue_dlq_events()
    logger.info(f"DLQ requeue: {count} событий переведено в pending")
    return {"status": "ok", "requeued": count}


# --- Northbound API для бэкенда ---

@router.get("/external/tasks")
async def external_tasks(
    start: str = Query(..., description="ISO UTC datetime"),
    end: str = Query(..., description="ISO UTC datetime"),
    force: bool = Query(default=False),
):
    """
    GET /external/tasks — northbound API для бэкенда.
    Бэкенд думает что это mock_testing_system.
    Возвращает список задач из LMS в формате который ожидает бэкенд.
    """
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Невалидный формат даты. Ожидается ISO UTC datetime."
        )

    if start_dt.tzinfo is None or end_dt.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="Даты должны быть в UTC (с timezone info)."
        )

    if end_dt <= start_dt:
        raise HTTPException(
            status_code=422,
            detail="end должен быть позже start."
        )

    logger.info(
        f"GET /external/tasks: start={start} end={end} force={force}"
    )

    try:
        tasks = await get_external_tasks(start_dt, end_dt, force)
    except Exception as e:
        logger.error(f"Ошибка получения tasks из LMS: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Source недоступен: {str(e)}"
        )

    return tasks


@router.get("/debug/events")
async def debug_events(limit: int = 20, status: str = None):
    """Просмотр событий в БД (отладка)."""
    import aiosqlite
    from core.config import settings

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        if status:
            query = "SELECT * FROM events_outbox WHERE send_status = ? ORDER BY id DESC LIMIT ?"
            params = (status, limit)
        else:
            query = "SELECT * FROM events_outbox ORDER BY id DESC LIMIT ?"
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            events = []
            for row in rows:
                d = dict(row)
                if d.get("raw_json"):
                    d["raw_json"] = d["raw_json"][:200] + "..."
                events.append(d)

    return {"count": len(events), "events": events}