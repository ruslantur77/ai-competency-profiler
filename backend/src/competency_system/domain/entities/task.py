from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from competency_system.domain.entities import Entity
from competency_system.domain.value_objects import (
    LLMFeedbackType,
    TaskStatus,
    TaskType,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel

if TYPE_CHECKING:
    from competency_system.domain.entities import (
        Candidate,
        Category,
        Competency,
        SubCompetency,
    )


@dataclass(kw_only=True)
class TaskCategoryNode(Entity):
    task_id: UUID = UUID(int=0)
    category_id: UUID
    position: int = 0
    task: Task | None = None
    category: Category | None = None


@dataclass(kw_only=True)
class TaskCompetencyNode(Entity):
    task_id: UUID = UUID(int=0)
    competency_id: UUID
    category_id: UUID
    is_required: bool = True
    position: int = 0
    task: Task | None = None
    competency: Competency | None = None
    category: Category | None = None


@dataclass(kw_only=True)
class TaskSubCompetencyNode(Entity):
    task_id: UUID = UUID(int=0)
    sub_competency_id: UUID
    competency_id: UUID
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = 1.0
    position: int = 0
    task: Task | None = None
    sub_competency: SubCompetency | None = None
    competency: Competency | None = None


@dataclass(kw_only=True)
class Task(Entity):
    """Task from the assessment system."""

    external_id: str
    title: str
    description: str = ""
    type: TaskType = TaskType.CODE
    status: TaskStatus = TaskStatus.PENDING
    error_message: str | None = None
    category_nodes: list[TaskCategoryNode] = field(default_factory=list)
    competency_nodes: list[TaskCompetencyNode] = field(default_factory=list)
    sub_competency_nodes: list[TaskSubCompetencyNode] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        return self.status == TaskStatus.READY


@dataclass(kw_only=True)
class TestResultQuestionAnswer(Entity):
    test_result_id: UUID
    question: str = ""
    answer: str = ""
    position: int
    test_result: TestResult | None = None


@dataclass(kw_only=True)
class TestResultLLMFeedbackItem(Entity):
    assessment_id: UUID
    type: LLMFeedbackType
    value: str = ""
    position: int
    assessment: TestResultLLMAssessment | None = None


@dataclass(kw_only=True)
class TestResultLLMAssessment(Entity):
    test_result_id: UUID
    passed: bool = False
    score: float = 0.0
    feedback: str = ""
    criteria_version: str = ""
    raw_test_score: float = 0.0
    penalized_test_score: float = 0.0
    attempt_penalty_applied: bool = False
    final_score: float = 0.0
    test_result: TestResult | None = None
    feedback_items: list[TestResultLLMFeedbackItem] = field(default_factory=list)


@dataclass(kw_only=True)
class TestResult(Entity):
    candidate_id: UUID
    task_id: UUID
    passed: bool = False
    score: float = 0.0
    attempts: int = 1
    code_submitted: str | None = None
    question_answers: list[TestResultQuestionAnswer] = field(default_factory=list)
    llm_assessment: TestResultLLMAssessment | None = None
    task: Task | None = None
    candidate: Candidate | None = None

    @property
    def normalized_score(self) -> float:
        if self.score <= 1.0:
            return max(0.0, min(1.0, self.score))
        return max(0.0, min(1.0, self.score / 100.0))
