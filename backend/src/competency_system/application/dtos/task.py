from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from competency_system.application.dtos.base import BaseDTO
from competency_system.domain.value_objects.enums import (
    LLMFeedbackType,
    TaskMappingStatus,
    TaskType,
)


class TaskCompetencyMappingDTO(BaseDTO):
    """DTO для маппинга задачи на компетенцию."""

    sub_competency_id: UUID
    weight: float


class TaskCategorySelectionDTO(BaseDTO):
    id: UUID | None = None
    llm_id: int | None = None


class TaskCategoryExtractionResultDTO(BaseDTO):
    categories: list[TaskCategorySelectionDTO]


class TaskCompetencySelectionDTO(BaseDTO):
    id: UUID | None = None
    llm_id: int | None = None


class TaskCompetencyExtractionResultDTO(BaseDTO):
    competencies: list[TaskCompetencySelectionDTO]


class TaskSubCompetencySelectionDTO(BaseDTO):
    id: UUID | None = None
    llm_id: int | None = None
    weight: float = 1.0


class TaskSubCompetencyExtractionResultDTO(BaseDTO):
    sub_competencies: list[TaskSubCompetencySelectionDTO]


class TaskMappingExtractionResultDTO(BaseDTO):
    """Final normalized mapping output."""

    mappings: list[TaskCompetencyMappingDTO]


class TaskDTO(BaseDTO):
    """DTO для задачи из тестирующей системы."""

    id: UUID
    external_id: str
    title: str
    description: str
    type: TaskType
    competency_mappings: list[TaskCompetencyMappingDTO]
    mapping_validated: bool
    mapping_status: TaskMappingStatus = TaskMappingStatus.PENDING
    mapping_error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ExternalTaskDTO(BaseDTO):
    external_id: str
    title: str
    description: str
    type: TaskType
    tags: list[str] = Field(default_factory=list)

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower()
        return value


class SyncTasksResultDTO(BaseDTO):
    synced_tasks: list[TaskDTO]


class TaskSyncCommandDTO(BaseDTO):
    tasks: list[ExternalTaskDTO]


class CandidateTaskAssessmentDTO(BaseDTO):
    event_id: str
    vacancy_id: UUID
    candidate_external_id: str
    task_external_id: str
    type: TaskType
    code: str | None = None
    question_answers: list[dict[str, str]] = Field(default_factory=list)
    passed: int = 0
    total: int = 0
    attempts: int = 1
    duration_seconds: int = 0

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower()
        return value


class LLMFeedbackItemDTO(BaseDTO):
    type: LLMFeedbackType
    value: str
    position: int | None = None


class LLMCodeAssessmentDTO(BaseDTO):
    passed: bool
    score: float
    feedback: str = ""
    feedback_items: list[LLMFeedbackItemDTO] = Field(default_factory=list)


class TestResultDTO(BaseDTO):
    """DTO для результата теста."""

    id: UUID
    candidate_id: UUID
    task_id: UUID
    passed: bool
    score: float
    attempts: int
    code_submitted: str | None
    question_answers: list[dict[str, str]]
    llm_assessment: dict[str, object] | None
    created_at: datetime
