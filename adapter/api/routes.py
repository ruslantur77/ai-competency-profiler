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