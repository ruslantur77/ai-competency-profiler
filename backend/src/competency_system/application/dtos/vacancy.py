from __future__ import annotations

from datetime import datetime
from enum import StrEnum
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
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VacancyListItemDTO(BaseDTO):
    id: UUID
    name: str
    status: VacancyStatus
    deleted_at: datetime | None = None
    created_at: datetime


class VacancyStatusUpdateDTO(BaseDTO):
    status: VacancyStatus


class VacancyCreateDTO(BaseDTO):
    name: str
    description: str


class VacancyUpdateDTO(BaseDTO):
    name: str


class VacancyGraphNodeMode(StrEnum):
    EXISTING = "existing"
    NEW = "new"


class VacancyGraphSubCompetencyInputDTO(BaseDTO):
    model_config = ConfigDict(extra="forbid")
    mode: VacancyGraphNodeMode
    id: UUID | None = None
    temp_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    target_level: CompetencyLevel = CompetencyLevel.BEGINNER
    weight: float = 1.0

    @model_validator(mode="after")
    def _validate_mode_fields(self) -> VacancyGraphSubCompetencyInputDTO:
        if self.mode == VacancyGraphNodeMode.EXISTING:
            if self.id is None:
                raise ValueError("Existing sub-competency requires 'id'")
            if self.temp_id is not None:
                raise ValueError("Existing sub-competency cannot include 'temp_id'")
            if self.name is not None:
                raise ValueError("Existing sub-competency cannot include 'name'")
            if self.description is not None:
                raise ValueError("Existing sub-competency cannot include 'description'")
            return self

        if self.id is not None:
            raise ValueError("New sub-competency cannot include 'id'")
        if self.temp_id is None:
            raise ValueError("New sub-competency requires 'temp_id'")
        if not self.name or not self.name.strip():
            raise ValueError("New sub-competency requires non-empty 'name'")
        return self


class VacancyGraphCompetencyInputDTO(BaseDTO):
    model_config = ConfigDict(extra="forbid")
    mode: VacancyGraphNodeMode
    id: UUID | None = None
    temp_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    is_required: bool = True
    sub_competencies: list[VacancyGraphSubCompetencyInputDTO] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def _validate_mode_fields(self) -> VacancyGraphCompetencyInputDTO:
        if self.mode == VacancyGraphNodeMode.EXISTING:
            if self.id is None:
                raise ValueError("Existing competency requires 'id'")
            if self.temp_id is not None:
                raise ValueError("Existing competency cannot include 'temp_id'")
            if self.name is not None:
                raise ValueError("Existing competency cannot include 'name'")
            if self.description is not None:
                raise ValueError("Existing competency cannot include 'description'")
            return self

        if self.id is not None:
            raise ValueError("New competency cannot include 'id'")
        if self.temp_id is None:
            raise ValueError("New competency requires 'temp_id'")
        if not self.name or not self.name.strip():
            raise ValueError("New competency requires non-empty 'name'")
        return self


class VacancyGraphCategoryInputDTO(BaseDTO):
    model_config = ConfigDict(extra="forbid")
    mode: VacancyGraphNodeMode
    id: UUID | None = None
    temp_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    emoji: str | None = None
    competencies: list[VacancyGraphCompetencyInputDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_mode_fields(self) -> VacancyGraphCategoryInputDTO:
        if self.mode == VacancyGraphNodeMode.EXISTING:
            if self.id is None:
                raise ValueError("Existing category requires 'id'")
            if self.temp_id is not None:
                raise ValueError("Existing category cannot include 'temp_id'")
            if self.name is not None:
                raise ValueError("Existing category cannot include 'name'")
            if self.description is not None:
                raise ValueError("Existing category cannot include 'description'")
            if self.emoji is not None:
                raise ValueError("Existing category cannot include 'emoji'")
            return self

        if self.id is not None:
            raise ValueError("New category cannot include 'id'")
        if self.temp_id is None:
            raise ValueError("New category requires 'temp_id'")
        if not self.name or not self.name.strip():
            raise ValueError("New category requires non-empty 'name'")
        return self


class VacancyGraphUpdateDTO(BaseDTO):
    model_config = ConfigDict(extra="forbid")
    categories: list[VacancyGraphCategoryInputDTO]
    error_message: str | None = None


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


class VacancySuggestionBulkDecisionDTO(BaseDTO):
    decisions: list[VacancySuggestionDecisionDTO] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_suggestion_ids(self) -> VacancySuggestionBulkDecisionDTO:
        suggestion_ids = [item.suggestion_id for item in self.decisions]
        if len(set(suggestion_ids)) != len(suggestion_ids):
            raise ValueError("Duplicate suggestion_id values are not allowed")
        return self
