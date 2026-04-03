from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.competency_level import CompetencyLevel


@dataclass(kw_only=True)
class SubCompetency(Entity):
    """Sub-competency in the canonical ontology."""

    competency_id: UUID = UUID(int=0)
    name: str
    description: str = ""
    weight: float = 1.0
    competency: Competency | None = None


@dataclass(kw_only=True)
class Competency(Entity):
    """Competency in the canonical ontology."""

    category_id: UUID
    name: str
    description: str = ""
    sub_competencies: list[SubCompetency] = field(default_factory=list)
    category: Category | None = None

    def calculate_level(self, achieved_subcompetency_ids: set[UUID]) -> CompetencyLevel:
        if not self.sub_competencies:
            return CompetencyLevel.NONE

        total_weight = sum(
            max(0.0, min(1.0, sub.weight)) for sub in self.sub_competencies
        )
        if total_weight <= 0:
            return CompetencyLevel.NONE

        achieved_weight = sum(
            max(0.0, min(1.0, sub.weight))
            for sub in self.sub_competencies
            if sub.id in achieved_subcompetency_ids
        )
        ratio = achieved_weight / total_weight
        return _ratio_to_level(ratio)


@dataclass(kw_only=True)
class Category(Entity):
    """Competency category."""

    name: str
    description: str = ""
    emoji: str = "📋"
    competencies: list[Competency] = field(default_factory=list)


def _ratio_to_level(ratio: float) -> CompetencyLevel:
    clamped = max(0.0, min(1.0, ratio))
    if clamped <= 0.0:
        return CompetencyLevel.NONE
    if clamped < 0.2:
        return CompetencyLevel.NOVICE
    if clamped < 0.4:
        return CompetencyLevel.BEGINNER
    if clamped < 0.6:
        return CompetencyLevel.INTERMEDIATE
    if clamped < 0.8:
        return CompetencyLevel.ADVANCED
    return CompetencyLevel.EXPERT
