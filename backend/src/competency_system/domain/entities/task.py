from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.enums import TaskMappingStatus, TaskType


@dataclass(kw_only=True)
class TaskCompetencyMapping:
    """Связь задания с subcompetency.

    weight (0.0-1.0) - насколько задание покрывает subcompetency.
    """

    sub_competency_id: UUID
    weight: float = 1.0


@dataclass(kw_only=True)
class Task(Entity):
    """Задание из тестирующей системы."""

    external_id: str
    title: str
    description: str = ""
    type: TaskType = TaskType.CODE

    # Маппинг на компетенции
    competency_mappings: list[TaskCompetencyMapping] = field(default_factory=list)
    mapping_validated: bool = False
    mapping_status: TaskMappingStatus = TaskMappingStatus.PENDING
    mapping_error_message: str | None = None


@dataclass(kw_only=True)
class TestResult(Entity):
    """Результат выполнения задания кандидатом."""

    candidate_id: UUID
    task_id: UUID

    # Результат
    passed: bool = False
    score: float = 0.0  # 0-100
    attempts: int = 1

    # Для CODE заданий
    code_submitted: str | None = None
    question_answers: list[dict[str, str]] = field(default_factory=list)
    llm_assessment: dict[str, object] | None = None

    @property
    def normalized_score(self) -> float:
        """Нормализованный score в диапазоне [0, 1]."""
        return self.score / 100.0
