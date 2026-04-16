from __future__ import annotations

from datetime import datetime
from uuid import UUID

from competency_system.application.dtos.base import BaseDTO
from competency_system.application.dtos.task import TestResultDTO
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import AssessmentStatus


class CandidateListItemDto(BaseDTO):
    """Candidate list item DTO."""

    id: UUID
    external_id: str
    vacancy_id: UUID
    status: AssessmentStatus = AssessmentStatus.PENDING
    last_assessment_at: datetime | None = None


class CandidateDTO(BaseDTO):
    """DTO для кандидата."""

    id: UUID
    external_id: str
    achieved_subcompetency_ids: set[UUID]
    assessment_status: AssessmentStatus
    last_assessment_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CompetencyScoreDTO(BaseDTO):
    """DTO для оценки компетенции."""

    competency_id: UUID
    level: CompetencyLevel
    confidence: float


class CandidateProfileDTO(BaseDTO):
    """DTO для профиля кандидата с оценками."""

    candidate_id: UUID
    external_id: str
    competency_scores: list[CompetencyScoreDTO]
    total_score: float


class CandidateAssessmentResultDTO(BaseDTO):
    candidate_profile: CandidateProfileDTO
    test_result: TestResultDTO
