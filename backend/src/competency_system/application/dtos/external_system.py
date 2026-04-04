from __future__ import annotations

from competency_system.application.dtos.base import BaseDTO
from competency_system.domain.value_objects.enums import TaskType


class ExternalTaskRecord(BaseDTO):
    external_id: str
    title: str
    description: str
    type: TaskType
    tags: list[str]


class ExternalTaskAssessmentPayload(BaseDTO):
    candidate_external_id: str
    task_external_id: str
    type: TaskType
    code: str | None = None
    passed: int = 0
    total: int = 0
    attempts: int = 1
    duration_seconds: int = 0
