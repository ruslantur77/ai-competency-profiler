from __future__ import annotations

from uuid import UUID

from pydantic import Field, model_validator

from competency_system.application.dtos.base import BaseDTO
from competency_system.domain.value_objects.competency_level import CompetencyLevel


class SubCompetencyDTO(BaseDTO):
    """DTO для подкомпетенции."""

    id: UUID
    competency_id: UUID
    name: str
    description: str
    weight: float
    target_level: CompetencyLevel


class CompetencyDTO(BaseDTO):
    """DTO для компетенции."""

    id: UUID
    category_id: UUID
    name: str
    description: str
    sub_competencies: list[SubCompetencyDTO]


class CategoryDTO(BaseDTO):
    """DTO для категории."""

    id: UUID
    name: str
    description: str
    emoji: str
    competencies: list[CompetencyDTO]


class CategoryCreateDTO(BaseDTO):
    name: str
    description: str = ""
    emoji: str = "📋"


class CategoryUpdateDTO(BaseDTO):
    name: str | None = None
    description: str | None = None
    emoji: str | None = None

    @model_validator(mode="after")
    def _validate_non_empty_update(self) -> CategoryUpdateDTO:
        if self.name is None and self.description is None and self.emoji is None:
            raise ValueError("At least one field must be provided for update")
        return self


class CompetencyCreateDTO(BaseDTO):
    category_id: UUID
    name: str
    description: str = ""


class CompetencyUpdateDTO(BaseDTO):
    category_id: UUID | None = None
    name: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _validate_non_empty_update(self) -> CompetencyUpdateDTO:
        if self.category_id is None and self.name is None and self.description is None:
            raise ValueError("At least one field must be provided for update")
        return self


class SubCompetencyCreateDTO(BaseDTO):
    competency_id: UUID
    name: str
    description: str = ""
    weight: float = Field(default=1.0, ge=0.0)
    target_level: CompetencyLevel = CompetencyLevel.EXPERT


class SubCompetencyUpdateDTO(BaseDTO):
    competency_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    weight: float | None = Field(default=None, ge=0.0)
    target_level: CompetencyLevel | None = None

    @model_validator(mode="after")
    def _validate_non_empty_update(self) -> SubCompetencyUpdateDTO:
        if (
            self.competency_id is None
            and self.name is None
            and self.description is None
            and self.weight is None
            and self.target_level is None
        ):
            raise ValueError("At least one field must be provided for update")
        return self
