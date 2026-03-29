from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from competency_system.domain.value_objects.enums import TaskType


@dataclass(frozen=True)
class ExternalTaskRecord:
    external_id: str
    title: str
    description: str
    type: TaskType
    tags: list[str]


@dataclass(frozen=True)
class ExternalTaskAssessmentPayload:
    candidate_external_id: str
    task_external_id: str
    type: TaskType
    code: str | None = None
    passed: int = 0
    total: int = 0
    attempts: int = 1
    duration_seconds: int = 0


class ExternalTestingSystemGateway(Protocol):
    async def list_tasks(self) -> list[ExternalTaskRecord]: ...
