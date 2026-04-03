from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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

    @property
    def achieved_subcompetency_ids(self) -> set[UUID]:
        return {item.sub_competency_id for item in self.achievements}

    @achieved_subcompetency_ids.setter
    def achieved_subcompetency_ids(self, value: set[UUID]) -> None:
        existing = {item.sub_competency_id: item for item in self.achievements}
        kept: list[CandidateSubCompetencyAchievement] = []
        for sub_id in value:
            if sub_id in existing:
                kept.append(existing[sub_id])
            else:
                kept.append(
                    CandidateSubCompetencyAchievement(
                        candidate_id=self.id,
                        sub_competency_id=sub_id,
                        achieved_at=datetime.now(UTC),
                    )
                )
        self.achievements = kept

    @property
    def assessment_status(self) -> AssessmentStatus:
        return self.status

    @assessment_status.setter
    def assessment_status(self, value: AssessmentStatus) -> None:
        self.status = value


@dataclass(kw_only=True)
class CompetencyScore:
    """Оценка компетенции для кандидата."""

    competency_id: UUID
    level: CompetencyLevel
    confidence: float = 1.0
