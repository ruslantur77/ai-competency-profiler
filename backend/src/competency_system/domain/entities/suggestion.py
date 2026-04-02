from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects import (
    CompetencyLevel,
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
)

if TYPE_CHECKING:
    from competency_system.domain.entities.competency import Category, Competency
    from competency_system.domain.entities.vacancy import Vacancy


@dataclass(kw_only=True)
class VacancyGraphSuggestion(Entity):
    """LLM proposal that requires expert decision."""

    vacancy_id: UUID
    stage: SuggestionStage
    entity_type: SuggestionEntityType
    status: SuggestionStatus = SuggestionStatus.PENDING

    name: str
    description: str = ""
    reason: str = ""

    parent_category_id: UUID | None = None
    parent_competency_id: UUID | None = None

    is_required: bool | None = None
    target_level: CompetencyLevel | None = None
    weight: float | None = None

    vacancy: Vacancy | None = None
    parent_category: Category | None = None
    parent_competency: Competency | None = None
