import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from pipeline.converter import extract_all_events
from competency.client import CompetencyClient, TaskNotSyncedError, WebhookConfigError
from competency.schemas import CandidateTaskAssessmentDTO
from core.config import settings
from core.logging import logger
from db import repository
from lms.client import LmsClient


async def _fetch_and_store(lms_client: LmsClient, now: datetime) -> int:
    """
    Получаем прогресс из LMS и сохраняем новые события в outbox.
    Обходим только курсы из SOURCE_COURSE_IDS с маппингом на вакансию.
    """
    last_sync = await repository.get_last_sync_time()
    if not last_sync:
        last_sync = now - timedelta(minutes=settings.initial_lookback_minutes)
        logger.info(
            f"Первый запуск. Берём данные за последние "
            f"{settings.initial_lookback_minutes} мин."
        )

    course_ids = settings.get_course_ids()
    if not course_ids:
        logger.warning("SOURCE_COURSE_IDS пустой — нечего синкать")
        return 0

    new_events_count = 0

    try:
        all_progress = await lms_client.get_user_progress(
            updated_from=last_sync.strftime("%Y-%m-%dT%H:%M:%SZ"),
            updated_to=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
    except Exception as e:
        logger.error(f"Ошибка при получении прогресса из LMS: {e}")
        return 0

    for course_id in course_ids:
        vacancy_id = settings.get_vacancy_id(course_id)
        if not vacancy_id:
            logger.warning(
                f"Нет маппинга course_id={course_id} → vacancy_id, пропускаем"
            )
            continue

        for user_progress in all_progress:
            events = extract_all_events(course_id, user_progress, vacancy_id)

            for event_id, dto, raw in events:
                is_new = await repository.upsert_event(
                    event_id=event_id,
                    course_id=course_id,
                    vacancy_id=vacancy_id,
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

    logger.info(f"Новых событий из LMS: {new_events_count}")
    await repository.set_last_sync_time(now)
    return new_events_count


async def _send_pending(competency_client: CompetencyClient) -> tuple[int, int, int]:
    """
    Отправляем pending события в webhook.
    Возвращает (sent, failed_to_dlq, skipped_not_synced).
    """
    pending = await repository.get_pending_events(
        limit=settings.batch_size_outbox
    )
    if not pending:
        return 0, 0, 0

    logger.info(f"Отправляю {len(pending)} pending событий...")
    sent = 0
    failed = 0
    skipped = 0

    async with httpx.AsyncClient() as http_client:
        for row in pending:
            dto = CandidateTaskAssessmentDTO(
                event_id=row["event_id"],
                vacancy_id=row["vacancy_id"],
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

            except TaskNotSyncedError as e:
                # Таск не синкнут — оставляем pending, попробуем позже
                logger.warning(f"Таск не синкнут, pending: {e}")
                skipped += 1

            except WebhookConfigError as e:
                # Конфигурационная ошибка — сразу в DLQ
                logger.error(f"Конфиг ошибка webhook, DLQ: {e}")
                await repository.mark_event_failed(
                    row["event_id"], str(e), settings.webhook_max_attempts
                )
                failed += 1

            except Exception as e:
                err_msg = str(e)
                logger.error(
                    f"Ошибка отправки event_id={row['event_id']}: {err_msg}"
                )
                await repository.mark_event_failed(
                    row["event_id"], err_msg, row["send_attempts"] + 1
                )
                failed += 1

    logger.info(
        f"Webhook: sent={sent}, failed/dlq={failed}, "
        f"skipped(not synced)={skipped}"
    )
    return sent, failed, skipped


async def run_poll_cycle() -> dict:
    """Полный цикл поллинга."""
    now = datetime.now(timezone.utc)
    logger.info(f"=== Начало цикла ({now.isoformat()}) ===")

    lms_client = LmsClient()
    competency_client = CompetencyClient()

    new_events = await _fetch_and_store(lms_client, now)
    sent, failed, skipped = await _send_pending(competency_client)

    result = {
        "started_at": now.isoformat(),
        "new_events_fetched": new_events,
        "webhooks_sent": sent,
        "webhooks_failed_or_dlq": failed,
        "webhooks_skipped_not_synced": skipped,
    }
    logger.info(f"=== Цикл завершён: {result} ===")
    return result


async def polling_worker() -> None:
    """Фоновый воркер."""
    logger.info(f"Поллинг запущен. Интервал: {settings.poll_interval_seconds} сек.")
    while True:
        try:
            await run_poll_cycle()
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
        await asyncio.sleep(settings.poll_interval_seconds)