from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from celery import Celery
from celery.result import AsyncResult

from competency_system.application.ports.llm_jobs import (
    LLMJob,
    LLMJobQueuePort,
    LLMJobStatus,
    LLMJobType,
)

CELERY_DISPATCH_TASK_NAME = "competency_system.llm.dispatch"


@dataclass(slots=True)
class _SubmittedJobMeta:
    type: LLMJobType
    payload: dict[str, object]
    created_at: datetime


class CeleryLLMJobQueue(LLMJobQueuePort):
    def __init__(
        self,
        celery_app: Celery,
        *,
        queue_name: str,
    ) -> None:
        self._celery = celery_app
        self._queue_name = queue_name
        self._submitted: dict[UUID, _SubmittedJobMeta] = {}

    async def enqueue(
        self,
        *,
        job_type: LLMJobType,
        payload: dict[str, object],
    ) -> UUID:
        job = LLMJob(type=job_type, payload=dict(payload))
        self._submitted[job.id] = _SubmittedJobMeta(
            type=job_type,
            payload=dict(payload),
            created_at=job.created_at,
        )
        await asyncio.to_thread(
            self._celery.send_task,
            CELERY_DISPATCH_TASK_NAME,
            kwargs={
                "job_type": str(job_type),
                "payload": dict(payload),
            },
            queue=self._queue_name,
            task_id=str(job.id),
        )
        return job.id

    async def get(self, job_id: UUID) -> LLMJob | None:
        meta = self._submitted.get(job_id)
        if meta is None:
            return None

        result = await asyncio.to_thread(AsyncResult, str(job_id), app=self._celery)
        status = self._map_status(result.status)
        error_message = None
        if status == LLMJobStatus.FAILED and result.result is not None:
            error_message = str(result.result)

        return LLMJob(
            id=job_id,
            type=meta.type,
            payload=dict(meta.payload),
            status=status,
            error_message=error_message,
            created_at=meta.created_at,
            updated_at=datetime.now(UTC),
        )

    async def close(self) -> None:
        return None

    @staticmethod
    def _map_status(celery_status: str) -> LLMJobStatus:
        return {
            "PENDING": LLMJobStatus.QUEUED,
            "RECEIVED": LLMJobStatus.QUEUED,
            "STARTED": LLMJobStatus.PROCESSING,
            "RETRY": LLMJobStatus.PROCESSING,
            "SUCCESS": LLMJobStatus.COMPLETED,
            "FAILURE": LLMJobStatus.FAILED,
            "REVOKED": LLMJobStatus.FAILED,
        }.get(celery_status, LLMJobStatus.FAILED)
