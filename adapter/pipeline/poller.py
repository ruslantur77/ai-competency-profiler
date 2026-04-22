import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from pipeline.converter import extract_all_events
from competency.client import CompetencyClient
from competency.schemas import CandidateTaskAssessmentDTO
from core.config import settings
from core.logging import logger
from db import repository
from lms.client import LmsClient


async def _fetch_and_store(lms_client: LmsClient, now: datetime) -> int:
    """
    Шаг 1: Получаем данные из LMS и сохраняем новые в БД.
    Возвращает количество новых событий.
    """
    last_sync = await repository.get_last_sync_time()
    if not last_sync:
        last_sync = now - timedelta(days=settings.initial_lookback_days)
        logger.info(f"Первый запуск. Берём данные за последние {settings.initial_lookback_days} дн.")

    new_events_count = 0

    try:
        all_progress = await lms_client.get_user_progress(
            updated_from=last_sync.isoformat(),
            updated_to=now.isoformat(),
        )
    except Exception as e:
        logger.error(f"Ошибка при получении данных из LMS: {e}")
        return 0

    for user_progress in all_progress:
        events = extract_all_events(user_progress)

        for event_id, dto, raw in events:
            is_new = await repository.upsert_lms_event(
                event_id=event_id,
                lms_user_id=user_progress.user.id,
                task_external_id=dto.task_external_id,
                task_type=dto.type,
                passed=dto.passed,
                total=dto.total,
                attempts=dto.attempts,
                duration_seconds=dto.duration_seconds,
                code_submitted=dto.code,
                raw_data=raw,
                fetched_at=now,
            )
            if is_new:
                new_events_count += 1

    logger.info(f"Получено новых событий из LMS: {new_events_count}")

    # Обновляем время последнего успешного поллинга ТОЛЬКО если запрос прошёл
    await repository.set_last_sync_time(now)

    return new_events_count


async def _send_pending(competency_client: CompetencyClient) -> tuple[int, int]:
    """
    Шаг 2: Отправляем все pending-события в наш webhook.
    Возвращает (sent_count, failed_count).
    """
    pending = await repository.get_pending_events(limit=200)
    if not pending:
        return 0, 0

    logger.info(f"Отправляю {len(pending)} pending событий в webhook...")
    sent = 0
    failed = 0

    async with httpx.AsyncClient() as http_client:
        for row in pending:
            dto = CandidateTaskAssessmentDTO(
                event_id=row["event_id"],
                vacancy_id=settings.target_vacancy_id,
                candidate_external_id=str(row["lms_user_id"]),
                task_external_id=row["task_external_id"],
                type=row["task_type"],
                code=row["code_submitted"],
                passed=row["passed"],
                total=row["total"],
                attempts=row["attempts"],
                duration_seconds=row["duration_seconds"],
            )

            try:
                await competency_client.send_assessment(dto, http_client)
                await repository.mark_event_sent(row["event_id"])
                sent += 1
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Не удалось отправить event_id={row['event_id']}: {err_msg}")
                await repository.mark_event_failed(row["event_id"], err_msg)
                failed += 1

    logger.info(f"Webhook: отправлено={sent}, ошибок={failed}")
    return sent, failed


async def run_poll_cycle() -> dict:
    """
    Полный цикл: получить из LMS → сохранить в БД → отправить в webhook.
    Возвращает статистику цикла.
    """
    now = datetime.now(timezone.utc)
    logger.info(f"=== Начало цикла поллинга ({now.isoformat()}) ===")

    lms_client = LmsClient()
    competency_client = CompetencyClient()

    new_events = await _fetch_and_store(lms_client, now)
    sent, failed = await _send_pending(competency_client)

    result = {
        "started_at": now.isoformat(),
        "new_events_fetched": new_events,
        "webhooks_sent": sent,
        "webhooks_failed": failed,
    }
    logger.info(f"=== Цикл завершён: {result} ===")
    return result


async def polling_worker() -> None:
    """Фоновый воркер — запускает цикл каждые N секунд."""
    logger.info(
        f"Поллинг запущен. Интервал: {settings.poll_interval_seconds} сек."
    )
    while True:
        try:
            await run_poll_cycle()
        except Exception as e:
            logger.error(f"Критическая ошибка в polling_worker: {e}", exc_info=True)

        await asyncio.sleep(settings.poll_interval_seconds)