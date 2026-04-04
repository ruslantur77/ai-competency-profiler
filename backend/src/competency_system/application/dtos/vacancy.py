from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from competency_system.application.dtos.base import BaseDTO
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    VacancyStatus,
)


class VacancyCategoryNodeDTO(BaseDTO):
    id: UUID
    vacancy_id: UUID
    category_id: UUID
    position: int
    category_name: str = ""
    category_description: str = ""
    category_emoji: str = ""


class VacancyCompetencyNodeDTO(BaseDTO):
    id: UUID
    vacancy_id: UUID
    competency_id: UUID
    category_id: UUID
    is_required: bool
    position: int
    competency_name: str = ""
    competency_description: str = ""


class VacancySubCompetencyNodeDTO(BaseDTO):
    id: UUID
    vacancy_id: UUID
    sub_competency_id: UUID
    competency_id: UUID
    target_level: CompetencyLevel
    weight: float
    position: int
    sub_competency_name: str = ""
    sub_competency_description: str = ""


class VacancyDTO(BaseDTO):
    id: UUID
    name: str
    description: str
    status: VacancyStatus
    category_nodes: list[VacancyCategoryNodeDTO] = Field(default_factory=list)
    competency_nodes: list[VacancyCompetencyNodeDTO] = Field(default_factory=list)
    sub_competency_nodes: list[VacancySubCompetencyNodeDTO] = Field(
        default_factory=list
    )
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class VacancyListItemDTO(BaseDTO):
    id: UUID
    name: str
    status: VacancyStatus
    created_at: datetime


class VacancyStatusUpdateDTO(BaseDTO):
    status: VacancyStatus


class VacancyCreateDTO(BaseDTO):
    name: str
    description: str


class VacancyGraphSubCompetencyInputDTO(BaseDTO):
    id: UUID
    name: str
    description: str = ""
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = 1.0


class VacancyGraphCompetencyInputDTO(BaseDTO):
    id: UUID
    category_id: UUID
    name: str
    description: str = ""
    is_required: bool = True
    sub_competencies: list[VacancyGraphSubCompetencyInputDTO] = Field(
        default_factory=list
    )


class VacancyGraphCategoryInputDTO(BaseDTO):
    id: UUID
    name: str
    description: str = ""
    emoji: str = ""
    competencies: list[VacancyGraphCompetencyInputDTO] = Field(default_factory=list)


class VacancyGraphUpdateDTO(BaseDTO):
    categories: list[VacancyGraphCategoryInputDTO]
    error_message: str | None = None
    suggestion_decisions: list[VacancySuggestionDecisionDTO] = Field(
        default_factory=list
    )


class _StrictExtractionDTO(BaseDTO):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class _ExistingSelectionItemDTO(_StrictExtractionDTO):
    id: UUID | None = None
    llm_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _validate_identity_fields(self) -> _ExistingSelectionItemDTO:
        if self.id is None and self.llm_id is None:
            raise ValueError("Either 'id' or 'llm_id' must be provided")
        if self.id is not None and self.llm_id is not None:
            raise ValueError("Only one of 'id' or 'llm_id' can be provided")
        return self


class VacancyCategorySuggestionDTO(_ExistingSelectionItemDTO):
    name: str = ""
    description: str = ""
    emoji: str = "📋"
    reason: str = ""


class VacancyCategoryExtractionResultDTO(_StrictExtractionDTO):
    categories: list[VacancyCategorySuggestionDTO]


class VacancyCompetencySelectionDTO(_ExistingSelectionItemDTO):
    category_id: UUID | None = None
    name: str = ""
    description: str = ""
    is_required: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = ""


class VacancyCompetencySuggestionDTO(_StrictExtractionDTO):
    name: str
    description: str = ""
    is_required: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = ""


class VacancyCompetencyExtractionResultDTO(_StrictExtractionDTO):
    competencies: list[VacancyCompetencySelectionDTO]
    suggested_new: list[VacancyCompetencySuggestionDTO] = Field(default_factory=list)


class VacancySubCompetencySelectionDTO(_ExistingSelectionItemDTO):
    competency_id: UUID | None = None
    name: str = ""
    description: str = ""
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = ""


class VacancySubCompetencySuggestionDTO(_StrictExtractionDTO):
    name: str
    description: str = ""
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = ""


class VacancySubCompetencyExtractionResultDTO(_StrictExtractionDTO):
    sub_competencies: list[VacancySubCompetencySelectionDTO]
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
