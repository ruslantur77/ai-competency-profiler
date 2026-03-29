from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import AssessmentStatus


@dataclass(kw_only=True)
class Candidate(Entity):
    """Кандидат с достигнутыми компетенциями.

    Упрощенная версия: просто набор ID достигнутых subcompetencies.
    """

    external_id: str
    achieved_subcompetency_ids: set[UUID] = field(default_factory=set)
    assessment_status: AssessmentStatus = AssessmentStatus.PENDING
    last_assessment_at: datetime | None = None

    def has_subcompetency(self, subcompetency_id: UUID) -> bool:
        """Проверить наличие subcompetency у кандидата."""
        return subcompetency_id in self.achieved_subcompetency_ids


@dataclass(kw_only=True)
class CompetencyScore:
    """Оценка компетенции для кандидата."""

    competency_id: UUID
    level: CompetencyLevel
    confidence: float = 1.0
