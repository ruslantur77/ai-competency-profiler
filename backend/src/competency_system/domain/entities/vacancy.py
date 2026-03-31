from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.entities.competency import Category, Competency
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus


@dataclass(kw_only=True)
class VacancyCategoryNode(Entity):
    vacancy_id: UUID
    category_id: UUID
    position: int


@dataclass(kw_only=True)
class VacancyCompetencyNode(Entity):
    vacancy_id: UUID
    competency_id: UUID
    category_id: UUID
    is_required: bool = True
    position: int


@dataclass(kw_only=True)
class VacancySubCompetencyNode(Entity):
    vacancy_id: UUID
    sub_competency_id: UUID
    competency_id: UUID
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = 1.0
    position: int


@dataclass(kw_only=True)
class Vacancy(Entity):
    """Вакансия c нормализованным графом требований."""

    name: str
    description: str
    status: VacancyStatus = VacancyStatus.DRAFT
    error_message: str | None = None
    categories: list[Category] = field(default_factory=list)
    competencies: list[Competency] = field(default_factory=list)
    category_nodes: list[VacancyCategoryNode] = field(default_factory=list)
    competency_nodes: list[VacancyCompetencyNode] = field(default_factory=list)
    sub_competency_nodes: list[VacancySubCompetencyNode] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        return self.status == VacancyStatus.READY
