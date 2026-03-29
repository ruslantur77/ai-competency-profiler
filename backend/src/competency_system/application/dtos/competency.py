from __future__ import annotations

from uuid import UUID

from competency_system.application.dtos.base import BaseDTO
from competency_system.domain.value_objects.competency_level import CompetencyLevel


class SubCompetencyDTO(BaseDTO):
    """DTO для подкомпетенции."""

    id: UUID
    name: str
    description: str
    target_level: CompetencyLevel
    weight: float


class CompetencyDTO(BaseDTO):
    """DTO для компетенции."""

    id: UUID
    category_id: UUID
    name: str
    description: str
    is_required: bool
    sub_competencies: list[SubCompetencyDTO]


class CategoryDTO(BaseDTO):
    """DTO для категории."""

    id: UUID
    name: str
    description: str
    emoji: str
    competencies: list[CompetencyDTO]
