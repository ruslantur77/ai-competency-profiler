from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from typing import Any

from competency_system.application.use_cases.task import SyncTasksUseCase
from competency_system.infrastructure.database import create_engine_and_session_factory
from competency_system.infrastructure.external.testing_system import (
    HTTPTestingSystemGateway,
)
from competency_system.infrastructure.llm.job_queue import InMemoryLLMJobQueue
from competency_system.infrastructure.logging import configure_logging, get_logger
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.infrastructure.settings import LLMQueueBackend, get_settings
from competency_system.presentation.airflow.payloads import TaskSyncPayloadDTO

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task-sync-runner",
        description="Run SyncTasksUseCase for the provided UTC period.",
    )
    parser.add_argument("--start", required=True, help="UTC datetime in ISO-8601")
    parser.add_argument("--end", required=True, help="UTC datetime in ISO-8601")
    return parser


def _parse_payload(start: str, end: str) -> TaskSyncPayloadDTO:
    return TaskSyncPayloadDTO.model_validate(
        {
            "start": start,
            "end": end,
        }
    )


async def _run(start: datetime, end: datetime) -> dict[str, Any]:
    settings = get_settings()
    configure_logging(settings)
    db_engine, session_factory = create_engine_and_session_factory(settings)
    testing_gateway = HTTPTestingSystemGateway(settings)

    async def _noop_dispatcher(*_: object) -> None:
        return None

    llm_job_queue: Any
    if settings.llm_queue_backend == LLMQueueBackend.CELERY:
        from competency_system.infrastructure.llm.celery_app import create_celery_app
        from competency_system.infrastructure.llm.celery_job_queue import (
            CeleryLLMJobQueue,
        )

        llm_job_queue = CeleryLLMJobQueue(
            create_celery_app(settings),
            queue_name=settings.celery_queue_name,
        )
    else:
        llm_job_queue = InMemoryLLMJobQueue(_noop_dispatcher)

    try:
        use_case = SyncTasksUseCase(
            SQLAlchemyUnitOfWork(session_factory),
            testing_gateway,
            llm_job_queue,
        )
        result = await use_case.execute(start=start, end=end)
        return result.model_dump(mode="json")
    finally:
        await llm_job_queue.close()
        await testing_gateway.close()
        await db_engine.dispose()


def main() -> None:
    args = _build_parser().parse_args()
    payload = _parse_payload(args.start, args.end)
    result = asyncio.run(_run(payload.start, payload.end))
    logger.info(
        "task_sync_finished",
        period_start=payload.start.isoformat(),
        period_end=payload.end.isoformat(),
        synced_tasks_count=len(result.get("synced_tasks", [])),
    )


if __name__ == "__main__":
    main()
