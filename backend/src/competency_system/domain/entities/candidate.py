from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects import AssessmentStatus, CompetencyLevel

if TYPE_CHECKING:
    from competency_system.domain.entities.competency import SubCompetency
    from competency_system.domain.entities.task import TestResult
    from competency_system.domain.entities.vacancy import Vacancy


@dataclass(kw_only=True)
class CandidateSubCompetencyAchievement(Entity):
    candidate_id: UUID
    sub_competency_id: UUID
    achieved_at: datetime
    candidate: Candidate | None = None
    sub_competency: SubCompetency | None = None


@dataclass(kw_only=True)
class Candidate(Entity):
    """Candidate applying for a vacancy, with achieved sub-competencies."""

    external_id: str
    vacancy_id: UUID
    status: AssessmentStatus = AssessmentStatus.PENDING
    last_assessment_at: datetime | None = None
    vacancy: Vacancy | None = None
    achievements: list[CandidateSubCompetencyAchievement] = field(default_factory=list)
    test_results: list[TestResult] = field(default_factory=list)


@dataclass(kw_only=True)
class CompetencyScore:
    """Оценка компетенции для кандидата."""

    competency_id: UUID
    level: CompetencyLevel
    confidence: float = 1.0
