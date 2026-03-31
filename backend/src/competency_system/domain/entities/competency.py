from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.competency_level import CompetencyLevel


@dataclass(kw_only=True)
class SubCompetency(Entity):
    """Подкомпетенция в каноническом справочнике."""

    competency_id: UUID = UUID(int=0)
    name: str
    description: str = ""
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = 1.0


@dataclass(kw_only=True)
class Competency(Entity):
    """Компетенция в каноническом справочнике."""

    category_id: UUID
    name: str
    description: str = ""
    sub_competencies: list[SubCompetency] = field(default_factory=list)
    is_required: bool = True

    def calculate_level(self, achieved_sub_ids: set[UUID]) -> CompetencyLevel:
        if not self.sub_competencies:
            return CompetencyLevel.NONE

        total_weight = sum(
            min(max(sub.weight, 0.0), 1.0) for sub in self.sub_competencies
        )
        if total_weight <= 0.0:
            return CompetencyLevel.NONE

        achieved_weight = sum(
            min(max(sub.weight, 0.0), 1.0)
            for sub in self.sub_competencies
            if sub.id in achieved_sub_ids
        )

        if achieved_weight <= 0.0:
            return CompetencyLevel.NONE

        ratio = min(1.0, achieved_weight / total_weight)
        if ratio >= 0.8:
            return CompetencyLevel.EXPERT
        if ratio >= 0.6:
            return CompetencyLevel.ADVANCED
        if ratio >= 0.4:
            return CompetencyLevel.INTERMEDIATE
        if ratio >= 0.2:
            return CompetencyLevel.BEGINNER
        return CompetencyLevel.NOVICE


@dataclass(kw_only=True)
class Category(Entity):
    """Категория компетенций."""

    name: str
    description: str = ""
    emoji: str = "📋"
    competencies: list[Competency] = field(default_factory=list)
