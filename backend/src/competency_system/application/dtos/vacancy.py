from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from competency_system.application.dtos.base import BaseDTO
from competency_system.application.dtos.competency import (
    CategoryDTO,
    CompetencyDTO,
)
from competency_system.application.dtos.candidate import CandidateDTO
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    VacancyStatus,
)


class VacancyDTO(BaseDTO):
    """Vacancy DTO."""

    id: UUID
    name: str
    description: str
    status: VacancyStatus
    error_message: str | None = None
    candidates: list[Candidate] = field(default_factory=list)
    category_nodes: list[VacancyCategoryNode] = field(default_factory=list)
    competency_nodes: list[VacancyCompetencyNode] = field(default_factory=list)
    sub_competency_nodes: list[VacancySubCompetencyNode] = field(default_factory=list)
    suggestions: list[VacancyGraphSuggestion] = field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VacancyListItemDTO(BaseDTO):
    """DTO for vacancy list item."""

    id: UUID
    name: str
    status: VacancyStatus
    created_at: datetime


class VacancyStatusUpdateDTO(BaseDTO):
    status: VacancyStatus


class VacancyCreateDTO(BaseDTO):
    name: str
    description: str


class VacancyGraphUpdateDTO(BaseDTO):
    categories: list[CategoryDTO]
    error_message: str | None = None
    suggestion_decisions: list[VacancySuggestionDecisionDTO] = Field(
        default_factory=list
    )


class VacancyCategorySuggestionDTO(BaseDTO):
    id: UUID | None = None
    llm_id: int | None = None
    name: str = ""
    description: str = ""
    emoji: str = "📋"
    reason: str = ""


class VacancyCategoryExtractionResultDTO(BaseDTO):
    categories: list[VacancyCategorySuggestionDTO]
    suggested_new: list[VacancyCategorySuggestionDTO] = Field(default_factory=list)


class VacancyCompetencySuggestionDTO(BaseDTO):
    id: UUID | None = None
    llm_id: int | None = None
    category_id: UUID | None = None
    name: str = ""
    description: str = ""
    is_required: bool = True
    weight: float = 1.0
    required_level: CompetencyLevel = CompetencyLevel.BEGINNER
    reason: str = ""


class VacancyCompetencyExtractionResultDTO(BaseDTO):
    competencies: list[VacancyCompetencySuggestionDTO]
    suggested_new: list[VacancyCompetencySuggestionDTO] = Field(default_factory=list)


class VacancySubCompetencySuggestionDTO(BaseDTO):
    id: UUID | None = None
    llm_id: int | None = None
    competency_id: UUID | None = None
    name: str = ""
    description: str = ""
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = 1.0
    reason: str = ""


class VacancySubCompetencyExtractionResultDTO(BaseDTO):
    sub_competencies: list[VacancySubCompetencySuggestionDTO]
    suggested_new: list[VacancySubCompetencySuggestionDTO] = Field(default_factory=list)


class VacancyGraphSuggestionDTO(BaseDTO):
    id: UUID
    vacancy_id: UUID
    stage: SuggestionStage
    entity_type: SuggestionEntityType
    status: SuggestionStatus
    name: str
    description: str = ""
    reason: str = ""
    parent_category_id: UUID | None = None
    parent_competency_id: UUID | None = None
    is_required: bool | None = None
    target_level: CompetencyLevel | None = None
    weight: float | None = None


class VacancySuggestionDecisionDTO(BaseDTO):
    suggestion_id: UUID
    status: SuggestionStatus
