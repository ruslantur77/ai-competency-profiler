from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4


class LLMJobType(StrEnum):
    VACANCY_EXTRACTION = "vacancy_extraction"
    TASK_MAPPING = "task_mapping"
    CANDIDATE_CODE_ASSESSMENT = "candidate_code_assessment"


class LLMJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(kw_only=True)
class LLMJob:
    id: UUID = field(default_factory=uuid4)
    type: LLMJobType
    payload: dict[str, object] = field(default_factory=dict)
    status: LLMJobStatus = LLMJobStatus.QUEUED
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class LLMJobQueuePort(Protocol):
    # TODO: replace in-process runner with external queue + worker.
    async def enqueue(
        self,
        *,
        job_type: LLMJobType,
        payload: dict[str, object],
        runner: Callable[[], Awaitable[None]],
    ) -> UUID: ...

    async def get(self, job_id: UUID) -> LLMJob | None: ...
