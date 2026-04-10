from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from typing import Any

from competency_system.application.use_cases.task import SyncTasksUseCase
from competency_system.infrastructure.database import create_engine_and_session_factory
from competency_system.infrastructure.external.testing_system import (
    HTTPTestingSystemGateway,
)
from competency_system.infrastructure.llm.job_queue import InMemoryLLMJobQueue
from competency_system.infrastructure.logging import configure_logging, get_logger
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.presentation.airflow.payloads import TaskSyncPayloadDTO

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TaskSyncRunnerConfig:
    debug: bool
    environment: str
    log_level: str
    database_url: str
    testing_system_base_url: str
    testing_system_api_token: str
    llm_queue_backend: str
    redis_host: str
    redis_port: int
    redis_password: str
    celery_queue_name: str
    celery_result_expires_seconds: int

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/0"


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


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    return int(value)


def _normalize_database_url(raw: str) -> str:
    value = raw.strip()
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+asyncpg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    if value.startswith("postgresql+psycopg2://"):
        return value.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return value


def _build_database_url_from_db_env() -> str:
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASS")
    values: dict[str, str] = {}
    missing: list[str] = []
    for key in required:
        value = os.getenv(key)
        if value is None or value == "":
            missing.append(key)
            continue
        values[key] = value
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(
            "Database configuration is incomplete. Provide DATABASE_URL "
            f"or all DB_* variables. Missing: {missing_str}"
        )
    return (
        "postgresql+asyncpg://"
        f"{values['DB_USER']}:{values['DB_PASS']}@"
        f"{values['DB_HOST']}:{values['DB_PORT']}/{values['DB_NAME']}"
    )


def _load_runner_config() -> TaskSyncRunnerConfig:
    database_url_env = os.getenv("DATABASE_URL")
    database_url = (
        _normalize_database_url(database_url_env)
        if database_url_env
        else _build_database_url_from_db_env()
    )
    return TaskSyncRunnerConfig(
        debug=_env_bool("DEBUG", False),
        environment=os.getenv("ENVIRONMENT", "local"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        database_url=database_url,
        testing_system_base_url=os.getenv(
            "TESTING_SYSTEM_BASE_URL",
            "http://localhost:9000",
        ),
        testing_system_api_token=os.getenv("TESTING_SYSTEM_API_TOKEN", ""),
        llm_queue_backend=os.getenv("LLM_QUEUE_BACKEND", "inmemory").lower(),
        redis_host=os.getenv("REDIS_HOST", "127.0.0.1"),
        redis_port=_env_int("REDIS_PORT", 6379),
        redis_password=os.getenv("REDIS_PASSWORD", ""),
        celery_queue_name=os.getenv("CELERY_QUEUE_NAME", "llm_jobs"),
        celery_result_expires_seconds=_env_int("CELERY_RESULT_EXPIRES_SECONDS", 86400),
    )


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
