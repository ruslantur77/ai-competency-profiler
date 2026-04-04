from __future__ import annotations

import asyncio
from typing import Final

import httpx
from celery import Task
from sqlalchemy.exc import DBAPIError, OperationalError

from competency_system.application.llm_dispatch import dispatch_llm_job
from competency_system.application.ports.llm_jobs import LLMJobType
from competency_system.infrastructure.database import create_engine_and_session_factory
from competency_system.infrastructure.llm.celery_app import get_celery_app
from competency_system.infrastructure.llm.celery_job_queue import (
    CELERY_DISPATCH_TASK_NAME,
)
from competency_system.infrastructure.llm.errors import LLMAdapterError
from competency_system.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMGateway,
)
from competency_system.infrastructure.logging import get_logger
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.infrastructure.settings import Settings, get_settings

logger = get_logger(__name__).bind(component="llm_worker")
celery_app = get_celery_app()

TRANSIENT_EXCEPTIONS: Final[tuple[type[BaseException], ...]] = (
    LLMAdapterError,
    httpx.HTTPError,
    ConnectionError,
    TimeoutError,
    OSError,
    OperationalError,
    DBAPIError,
)


@celery_app.task(  # type: ignore[untyped-decorator]
    name=CELERY_DISPATCH_TASK_NAME,
    bind=True,
)
def dispatch_llm_job_task(
    self: Task,
    *,
    job_type: str,
    payload: dict[str, object],
) -> None:
    settings = get_settings()
    try:
        parsed_job_type = LLMJobType(job_type)
    except ValueError:
        logger.warning("llm_job_unknown_type", job_type=job_type)
        raise

    max_retries = max(0, settings.celery_retry_attempts - 1)
    try:
        asyncio.run(_run_dispatch(parsed_job_type, payload, settings))
    except TRANSIENT_EXCEPTIONS as exc:
        if self.request.retries >= max_retries:
            raise
        countdown = min(
            settings.celery_retry_backoff_max_seconds,
            settings.celery_retry_backoff_seconds * (2**self.request.retries),
        )
        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries) from exc


async def _run_dispatch(
    job_type: LLMJobType,
    payload: dict[str, object],
    settings: Settings,
) -> None:
    db_engine, session_factory = create_engine_and_session_factory(settings)
    llm_gateway = OpenAICompatibleLLMGateway(settings)
    try:
        await dispatch_llm_job(
            job_type,
            payload,
            uow=SQLAlchemyUnitOfWork(session_factory),
            llm_gateway=llm_gateway,
            vacancy_prompt_version=settings.llm_vacancy_prompt_version,
            task_prompt_version=settings.llm_task_prompt_version,
            code_prompt_version=settings.llm_code_prompt_version,
            max_parallel_requests=settings.llm_max_parallel_requests,
            stage_timeout_seconds=settings.llm_stage_timeout_seconds,
            max_suggested_new_per_stage=settings.llm_max_suggested_new_per_stage,
        )
    finally:
        await llm_gateway.close()
        await db_engine.dispose()
