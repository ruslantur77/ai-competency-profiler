from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
)


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
