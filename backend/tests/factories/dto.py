from __future__ import annotations

from datetime import UTC, datetime
from typing import NotRequired, TypedDict
from uuid import UUID, uuid4

from competency_system.application.dtos.candidate import (
    CandidateAssessmentResultDTO,
    CandidateProfileDTO,
    CompetencyScoreDTO,
)
from competency_system.application.dtos.ranking import (
    RankingBreakdownItemDTO,
    RankingItemDTO,
    VacancyRankingDTO,
)
from competency_system.application.dtos.task import (
    TaskDTO,
    TestResultDTO,
)
from competency_system.application.dtos.vacancy import VacancyDTO
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    TaskStatus,
    TaskType,
    VacancyStatus,
)


class VacancyDTOFields(TypedDict):
    id: NotRequired[UUID]
    name: NotRequired[str]
    description: NotRequired[str]
    status: NotRequired[VacancyStatus]


class TaskDTOFields(TypedDict):
    id: NotRequired[UUID]
    external_id: NotRequired[str]
    title: NotRequired[str]
    description: NotRequired[str]
    type: NotRequired[TaskType]
    status: NotRequired[TaskStatus]


class ApiDTOFactory:
    def make_vacancy(self, fields: VacancyDTOFields | None = None) -> VacancyDTO:
        data = fields or {}
        now = datetime.now(UTC)

        return VacancyDTO(
            id=data.get("id", uuid4()),
            name=data.get("name", "Backend Engineer"),
            description=data.get("description", "Build APIs"),
            status=data.get("status", VacancyStatus.READY),
            category_nodes=[],
            competency_nodes=[],
            sub_competency_nodes=[],
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def make_task(self, fields: TaskDTOFields | None = None) -> TaskDTO:
        data = fields or {}
        now = datetime.now(UTC)
        return TaskDTO(
            id=data.get("id", uuid4()),
            external_id=data.get("external_id", "task-1"),
            title=data.get("title", "API Task"),
            description=data.get("description", "Implement API"),
            type=data.get("type", TaskType.CODE),
            status=data.get("status", TaskStatus.DRAFT),
            category_nodes=[],
            competency_nodes=[],
            sub_competency_nodes=[],
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def make_candidate_profile(self) -> CandidateProfileDTO:
        return CandidateProfileDTO(
            candidate_id=uuid4(),
            external_id="candidate-1",
            competency_scores=[
                CompetencyScoreDTO(
                    competency_id=uuid4(),
                    competency_name="Backend",
                    competency_description="Backend competency",
                    category_id=uuid4(),
                    category_name="Engineering",
                    level=CompetencyLevel.ADVANCED,
                    confidence=0.8,
                )
            ],
            total_score=80.0,
        )

    def make_candidate_result(self) -> CandidateAssessmentResultDTO:
        now = datetime.now(UTC)
        profile = self.make_candidate_profile()
        return CandidateAssessmentResultDTO(
            candidate_profile=profile,
            test_result=TestResultDTO(
                id=uuid4(),
                candidate_id=profile.candidate_id,
                task_id=uuid4(),
                passed=True,
                score=85.0,
                attempts=1,
                code_submitted="print('ok')",
                question_answers=[],
                llm_assessment={
                    "score": 85,
                    "feedback_items": [
                        {"type": "positive", "value": "clear structure", "position": 0}
                    ],
                },
                created_at=now,
            ),
        )

    def make_ranking(self, vacancy_id: UUID) -> VacancyRankingDTO:
        return VacancyRankingDTO(
            vacancy_id=vacancy_id,
            rankings=[
                RankingItemDTO(
                    candidate_id=uuid4(),
                    candidate_external_id="candidate-1",
                    total_score=0.79,
                    required_match=0.7,
                    desired_match=1.0,
                    required_score=0.49,
                    desired_score=0.30,
                    breakdown=[
                        RankingBreakdownItemDTO(
                            competency_id=uuid4(),
                            competency_name="Backend",
                            required=True,
                            matched_weight=0.7,
                            total_weight=1.0,
                            coverage=0.7,
                            score_contribution=0.49,
                            matched_subcompetency_ids=[uuid4()],
                            total_subcompetency_ids=[uuid4()],
                        )
                    ],
                )
            ],
        )
