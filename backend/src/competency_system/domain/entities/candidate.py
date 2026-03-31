from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import AssessmentStatus


@dataclass(kw_only=True)
class CandidateSubCompetencyAchievement(Entity):
    candidate_id: UUID
    sub_competency_id: UUID
    achieved_at: datetime


@dataclass(kw_only=True)
class Candidate(Entity):
    """Кандидат с достигнутыми компетенциями."""

    external_id: str
    vacancy_id: UUID
    achievements: list[CandidateSubCompetencyAchievement] = field(default_factory=list)
    achieved_subcompetency_ids: set[UUID] = field(default_factory=set)
    status: AssessmentStatus = AssessmentStatus.PENDING
    last_assessment_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.achievements and not self.achieved_subcompetency_ids:
            self.achieved_subcompetency_ids = {
                achievement.sub_competency_id for achievement in self.achievements
            }
        elif self.achieved_subcompetency_ids and not self.achievements:
            self.achievements = [
                CandidateSubCompetencyAchievement(
                    candidate_id=self.id,
                    sub_competency_id=sub_competency_id,
                    achieved_at=self.updated_at,
                )
                for sub_competency_id in sorted(self.achieved_subcompetency_ids, key=str)
            ]

    def has_subcompetency(self, subcompetency_id: UUID) -> bool:
        """Проверить наличие subcompetency у кандидата."""
        return any(
            achievement.sub_competency_id == subcompetency_id
            for achievement in self.achievements
        )

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
