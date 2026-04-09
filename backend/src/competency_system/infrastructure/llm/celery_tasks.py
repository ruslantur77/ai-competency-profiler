from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Final

import httpx
from celery import Task
from sqlalchemy.exc import DBAPIError, OperationalError

from competency_system.application.llm.llm_dispatch import dispatch_llm_job
from competency_system.application.ports.llm_jobs import LLMJobType
from competency_system.infrastructure.database import create_engine_and_session_factory
from competency_system.infrastructure.llm.celery_app import celery_app
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
    started = perf_counter()
    settings = get_settings()
    task_id = str(getattr(self.request, "id", ""))
    retries = int(getattr(self.request, "retries", 0))
    job_logger = logger.bind(
        task_id=task_id,
        queue=settings.celery_queue_name,
        job_type=job_type,
        retry=retries,
    )
    job_logger.info(
        "llm_job_started",
        payload_summary={"keys": sorted(payload.keys()), "size": len(payload)},
    )
    try:
        parsed_job_type = LLMJobType(job_type)
    except ValueError:
        job_logger.exception("llm_job_unknown_type", payload=payload)
        raise

    max_retries = max(0, settings.celery_retry_attempts - 1)
    try:
        asyncio.run(_run_dispatch(parsed_job_type, payload, settings))
        duration_ms = round((perf_counter() - started) * 1000.0, 2)
        job_logger.info("llm_job_finished", status="success", duration_ms=duration_ms)
    except TRANSIENT_EXCEPTIONS as exc:
        if self.request.retries >= max_retries:
            duration_ms = round((perf_counter() - started) * 1000.0, 2)
            job_logger.exception(
                "llm_job_failed",
                status="failed",
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error=str(exc),
                payload=payload,
                attempts_made=self.request.retries + 1,
                max_retries=max_retries,
            )
            raise
        countdown = min(
            settings.celery_retry_backoff_max_seconds,
            settings.celery_retry_backoff_seconds * (2**self.request.retries),
        )
        job_logger.warning(
            "llm_job_retry_scheduled",
            error_type=type(exc).__name__,
            error=str(exc),
            countdown=countdown,
            attempts_made=self.request.retries + 1,
            max_retries=max_retries,
            payload_summary={"keys": sorted(payload.keys()), "size": len(payload)},
        )
        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries) from exc
    except Exception as exc:
        duration_ms = round((perf_counter() - started) * 1000.0, 2)
        job_logger.exception(
            "llm_job_failed",
            status="failed",
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
            error=str(exc),
            payload=payload,
            attempts_made=self.request.retries + 1,
            max_retries=max_retries,
        )
        raise


async def _run_dispatch(
    job_type: LLMJobType,
    payload: dict[str, object],
    settings: Settings,
) -> None:
    db_engine, session_factory = create_engine_and_session_factory(
        database_url=settings.database_url,
        debug=settings.debug,
    )
    llm_gateway = OpenAICompatibleLLMGateway(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
        model=settings.llm_model,
        retry_attempts=settings.llm_retry_attempts,
        reasoning_max_tokens=settings.llm_reasoning_max_tokens,
    )
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
