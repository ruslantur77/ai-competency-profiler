from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects import CompetencyLevel, VacancyStatus

if TYPE_CHECKING:
    from competency_system.domain.entities.candidate import Candidate
    from competency_system.domain.entities.competency import (
        Category,
        Competency,
        SubCompetency,
    )
    from competency_system.domain.entities.suggestion import VacancyGraphSuggestion


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
    candidates: list[Candidate] = field(default_factory=list)
    category_nodes: list[VacancyCategoryNode] = field(default_factory=list)
    competency_nodes: list[VacancyCompetencyNode] = field(default_factory=list)
    sub_competency_nodes: list[VacancySubCompetencyNode] = field(default_factory=list)
    suggestions: list[VacancyGraphSuggestion] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        return self.status == VacancyStatus.READY
