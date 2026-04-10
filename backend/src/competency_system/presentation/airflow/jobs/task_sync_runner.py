from __future__ import annotations

import argparse
import asyncio
from typing import Any

from competency_system.application.use_cases.task import SyncTasksUseCase
from competency_system.infrastructure.database import create_engine_and_session_factory
from competency_system.infrastructure.external.testing_system import (
    HTTPTestingSystemGateway,
)
from competency_system.infrastructure.llm.job_queue import InMemoryLLMJobQueue
from competency_system.infrastructure.logging import configure_logging, get_logger
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.presentation.airflow.jobs.task_sync_runtime import (
    TaskSyncRunnerConfig,
    load_runner_config,
)
from competency_system.presentation.airflow.payloads import TaskSyncPayloadDTO

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task-sync-runner",
        description="Run SyncTasksUseCase for the provided UTC period.",
    )
    parser.add_argument("--start", required=True, help="UTC datetime in ISO-8601")
    parser.add_argument("--end", required=True, help="UTC datetime in ISO-8601")
    parser.add_argument(
        "--force",
        default="false",
        help="Force full overwrite for synced tasks (true/false).",
    )
    return parser


def _parse_payload(start: str, end: str, force: str) -> TaskSyncPayloadDTO:
    return TaskSyncPayloadDTO.model_validate(
        {
            "start": start,
            "end": end,
            "force": force,
        }
    )


def _load_runner_config() -> TaskSyncRunnerConfig:
    return load_runner_config()


async def _run(
    payload: TaskSyncPayloadDTO,
    config: TaskSyncRunnerConfig,
) -> dict[str, Any]:
    configure_logging(log_level=config.log_level, environment=config.environment)
    db_engine, session_factory = create_engine_and_session_factory(
        database_url=config.database_url,
        debug=config.debug,
    )
    testing_gateway = HTTPTestingSystemGateway(
        base_url=config.testing_system_base_url,
        api_token=config.testing_system_api_token,
    )

    async def _noop_dispatcher(*_: object) -> None:
        return None

    llm_job_queue: Any
    if config.llm_queue_backend == "celery":
        from competency_system.infrastructure.llm.celery_app import create_celery_app
        from competency_system.infrastructure.llm.celery_job_queue import (
            CeleryLLMJobQueue,
        )

        llm_job_queue = CeleryLLMJobQueue(
            create_celery_app(
                redis_url=config.redis_url,
                queue_name=config.celery_queue_name,
                result_expires_seconds=config.celery_result_expires_seconds,
                log_level=config.log_level,
                environment=config.environment,
            ),
            queue_name=config.celery_queue_name,
        )
    else:
        llm_job_queue = InMemoryLLMJobQueue(_noop_dispatcher)

    try:
        use_case = SyncTasksUseCase(
            SQLAlchemyUnitOfWork(session_factory),
            testing_gateway,
            llm_job_queue,
        )
        result = await use_case.execute(
            start=payload.start,
            end=payload.end,
            force=payload.force,
        )
        return result.model_dump(mode="json")
    finally:
        await llm_job_queue.close()
        await testing_gateway.close()
        await db_engine.dispose()


def main() -> None:
    args = _build_parser().parse_args()
    payload = _parse_payload(args.start, args.end, args.force)
    config = _load_runner_config()
    result = asyncio.run(_run(payload, config))
    logger.info(
        "task_sync_finished",
        period_start=payload.start.isoformat(),
        period_end=payload.end.isoformat(),
        force=payload.force,
        synced_tasks_count=len(result.get("synced_tasks", [])),
    )


if __name__ == "__main__":
    main()
