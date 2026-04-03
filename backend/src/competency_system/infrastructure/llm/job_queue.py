from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from competency_system.application.ports.llm_jobs import (
    LLMJob,
    LLMJobQueuePort,
    LLMJobStatus,
    LLMJobType,
)


class InMemoryLLMJobQueue(LLMJobQueuePort):
    # TODO: replace with durable queue + separate worker process.
    def __init__(self) -> None:
        self._jobs: dict[UUID, LLMJob] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    async def enqueue(
        self,
        *,
        job_type: LLMJobType,
        payload: dict[str, object],
        runner: Callable[[], Awaitable[None]],
    ) -> UUID:
        job = LLMJob(type=job_type, payload=dict(payload))
        self._jobs[job.id] = job
        task = asyncio.create_task(self._run(job.id, runner))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job.id

    async def get(self, job_id: UUID) -> LLMJob | None:
        return self._jobs.get(job_id)

    async def close(self) -> None:
        for task in tuple(self._tasks):
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run(
        self,
        job_id: UUID,
        runner: Callable[[], Awaitable[None]],
    ) -> None:
        job = self._jobs[job_id]
        job.status = LLMJobStatus.PROCESSING
        job.updated_at = datetime.now(UTC)
        try:
            await runner()
        except Exception as exc:
            job.status = LLMJobStatus.FAILED
            job.error_message = str(exc)
            job.updated_at = datetime.now(UTC)
            return
        job.status = LLMJobStatus.COMPLETED
        job.updated_at = datetime.now(UTC)
