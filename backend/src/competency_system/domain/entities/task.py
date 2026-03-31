from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.enums import (
    LLMFeedbackType,
    TaskMappingStatus,
    TaskType,
)


@dataclass(kw_only=True)
class TaskSubCompetencyMapping(Entity):
    task_id: UUID = UUID(int=0)
    sub_competency_id: UUID
    weight: float = 1.0
    position: int = 0


@dataclass(kw_only=True)
class Task(Entity):
    """Задание из тестирующей системы."""

    external_id: str
    title: str
    description: str = ""
    type: TaskType = TaskType.CODE

    sub_competency_mappings: list[TaskSubCompetencyMapping] = field(
        default_factory=list
    )
    competency_mappings: list[TaskSubCompetencyMapping] = field(default_factory=list)
    mapping_validated: bool = False
    mapping_status: TaskMappingStatus = TaskMappingStatus.PENDING
    mapping_error_message: str | None = None

    def __post_init__(self) -> None:
        if self.sub_competency_mappings and not self.competency_mappings:
            self.competency_mappings = list(self.sub_competency_mappings)
        elif self.competency_mappings and not self.sub_competency_mappings:
            self.sub_competency_mappings = list(self.competency_mappings)


@dataclass(kw_only=True)
class TestResultQuestionAnswer(Entity):
    test_result_id: UUID
    question: str = ""
    answer: str = ""
    position: int


@dataclass(kw_only=True)
class TestResultLLMFeedbackItem(Entity):
    assessment_id: UUID
    type: LLMFeedbackType
    value: str = ""
    position: int


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

    def __post_init__(self) -> None:
        normalized_answers: list[TestResultQuestionAnswer] = []
        for position, answer in enumerate(self.question_answers):
            if isinstance(answer, TestResultQuestionAnswer):
                normalized_answers.append(answer)
                continue
            if isinstance(answer, dict):
                normalized_answers.append(
                    TestResultQuestionAnswer(
                        test_result_id=self.id,
                        question=str(answer.get("question", "")),
                        answer=str(answer.get("answer", "")),
                        position=position,
                    )
                )
        self.question_answers = normalized_answers

        if isinstance(self.llm_assessment, dict):
            feedback_raw = self.llm_assessment.get("feedback_items", [])
            feedback_items: list[TestResultLLMFeedbackItem] = []
            if isinstance(feedback_raw, list):
                for index, item in enumerate(feedback_raw):
                    if isinstance(item, dict):
                        item_type_raw = item.get("type", LLMFeedbackType.NEGATIVE.value)
                        try:
                            item_type = LLMFeedbackType(str(item_type_raw))
                        except ValueError:
                            item_type = LLMFeedbackType.NEGATIVE
                        position_raw = item.get("position", index)
                        try:
                            position = (
                                int(position_raw) if position_raw is not None else index
                            )
                        except (TypeError, ValueError):
                            position = index
                        feedback_items.append(
                            TestResultLLMFeedbackItem(
                                assessment_id=UUID(int=0),
                                type=item_type,
                                value=str(item.get("value", "")),
                                position=position,
                            )
                        )
                    else:
                        feedback_items.append(
                            TestResultLLMFeedbackItem(
                                assessment_id=UUID(int=0),
                                type=LLMFeedbackType.NEGATIVE,
                                value=str(item),
                                position=index,
                            )
                        )

            # Backward compatibility for existing payloads.
            if not feedback_items:
                strengths_raw = self.llm_assessment.get("strengths", [])
                issues_raw = self.llm_assessment.get("issues", [])
                if isinstance(strengths_raw, list):
                    feedback_items.extend(
                        TestResultLLMFeedbackItem(
                            assessment_id=UUID(int=0),
                            type=LLMFeedbackType.POSITIVE,
                            value=str(value),
                            position=position,
                        )
                        for position, value in enumerate(strengths_raw)
                    )
                if isinstance(issues_raw, list):
                    offset = len(feedback_items)
                    feedback_items.extend(
                        TestResultLLMFeedbackItem(
                            assessment_id=UUID(int=0),
                            type=LLMFeedbackType.NEGATIVE,
                            value=str(value),
                            position=offset + position,
                        )
                        for position, value in enumerate(issues_raw)
                    )
            self.llm_assessment = TestResultLLMAssessment(
                test_result_id=self.id,
                passed=bool(self.llm_assessment.get("passed", self.passed)),
                score=float(self.llm_assessment.get("score", self.score)),
                feedback=str(self.llm_assessment.get("feedback", "")),
                criteria_version=str(self.llm_assessment.get("criteria_version", "")),
                raw_test_score=float(self.llm_assessment.get("raw_test_score", 0.0)),
                penalized_test_score=float(
                    self.llm_assessment.get("penalized_test_score", 0.0)
                ),
                attempt_penalty_applied=bool(
                    self.llm_assessment.get("attempt_penalty_applied", False)
                ),
                final_score=float(self.llm_assessment.get("final_score", self.score)),
                feedback_items=feedback_items,
            )

    @property
    def normalized_score(self) -> float:
        return self.score / 100.0


TaskCompetencyMapping = TaskSubCompetencyMapping
