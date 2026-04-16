from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects import CompetencyLevel, VacancyStatus

if TYPE_CHECKING:
    from competency_system.domain.entities import (
        Candidate,
        Category,
        Competency,
        SubCompetency,
        VacancyGraphSuggestion,
    )


@dataclass(kw_only=True)
class VacancyCategoryNode(Entity):
    vacancy_id: UUID
    category_id: UUID
    position: int
    vacancy: Vacancy | None = None
    category: Category | None = None


@dataclass(kw_only=True)
class VacancyCompetencyNode(Entity):
    vacancy_id: UUID
    competency_id: UUID
    category_id: UUID
    is_required: bool = True
    position: int
    vacancy: Vacancy | None = None
    competency: Competency | None = None
    category: Category | None = None


@dataclass(kw_only=True)
class VacancySubCompetencyNode(Entity):
    vacancy_id: UUID
    sub_competency_id: UUID
    competency_id: UUID
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = 1.0
    position: int
    vacancy: Vacancy | None = None
    sub_competency: SubCompetency | None = None
    competency: Competency | None = None


@dataclass(kw_only=True)
class Vacancy(Entity):
    """Vacancy with a normalized requirements graph."""

    name: str
    description: str
    status: VacancyStatus = VacancyStatus.DRAFT
    error_message: str | None = None
    deleted_at: datetime | None = None
    candidates: list[Candidate] = field(default_factory=list)
    category_nodes: list[VacancyCategoryNode] = field(default_factory=list)
    competency_nodes: list[VacancyCompetencyNode] = field(default_factory=list)
    sub_competency_nodes: list[VacancySubCompetencyNode] = field(default_factory=list)
    suggestions: list[VacancyGraphSuggestion] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        return self.status == VacancyStatus.READY

    @property
    def requirement_competencies(self) -> list[Competency]:
        from competency_system.domain.entities import Competency, SubCompetency

        sub_by_competency: dict[UUID, list[SubCompetency]] = {}
        for node in self.sub_competency_nodes:
            base = node.sub_competency
            if base is None:
                continue
            sub_by_competency.setdefault(node.competency_id, []).append(
                SubCompetency(
                    id=base.id,
                    competency_id=base.competency_id,
                    name=base.name,
                    description=base.description,
                    weight=node.weight,
                    created_at=base.created_at,
                    updated_at=base.updated_at,
                )
            )
        return [
            Competency(
                id=c.competency.id,
                category_id=c.competency.category_id,
                name=c.competency.name,
                description=c.competency.description,
                sub_competencies=sub_by_competency.get(c.competency_id, []),
                created_at=c.competency.created_at,
                updated_at=c.competency.updated_at,
            )
            for c in self.competency_nodes
            if c.competency is not None
        ]
