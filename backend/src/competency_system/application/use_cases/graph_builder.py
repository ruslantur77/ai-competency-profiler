from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.domain.value_objects.competency_level import CompetencyLevel


class _GraphNodeDTO(Protocol):
    @property
    def mode(self) -> str | StrEnum: ...

    @property
    def id(self) -> UUID | None: ...

    @property
    def name(self) -> str | None: ...

    @property
    def description(self) -> str | None: ...


class GraphSubCompetencyDTO(_GraphNodeDTO, Protocol):
    @property
    def weight(self) -> float: ...

    @property
    def target_level(self) -> CompetencyLevel: ...


class GraphCompetencyDTO(_GraphNodeDTO, Protocol):
    @property
    def is_required(self) -> bool: ...

    @property
    def sub_competencies(self) -> Sequence[GraphSubCompetencyDTO]: ...


class GraphCategoryDTO(_GraphNodeDTO, Protocol):
    @property
    def emoji(self) -> str | None: ...

    @property
    def competencies(self) -> Sequence[GraphCompetencyDTO]: ...


@dataclass
class ResolvedCategory:
    category: Category
    dto: GraphCategoryDTO
    position: int


@dataclass
class ResolvedCompetency:
    competency: Competency
    dto: GraphCompetencyDTO
    category: Category
    position: int


@dataclass
class ResolvedSubCompetency:
    sub_competency: SubCompetency
    dto: GraphSubCompetencyDTO
    competency: Competency
    position: int


@dataclass
class ResolvedGraphPayload:
    categories_to_create: list[Category]
    competencies_to_create: list[Competency]
    sub_competencies_to_create: list[SubCompetency]
    categories: list[ResolvedCategory]
    competencies: list[ResolvedCompetency]
    sub_competencies: list[ResolvedSubCompetency]


class GraphEntityResolver:
    async def resolve(
        self, uow: UnitOfWork, categories_dto: Sequence[GraphCategoryDTO]
    ) -> ResolvedGraphPayload:
        categories_to_create: list[Category] = []
        competencies_to_create: list[Competency] = []
        sub_competencies_to_create: list[SubCompetency] = []
        categories: list[ResolvedCategory] = []
        competencies: list[ResolvedCompetency] = []
        sub_competencies: list[ResolvedSubCompetency] = []

        used_category_ids: set[UUID] = set()
        used_competency_ids: set[UUID] = set()
        used_sub_competency_ids: set[UUID] = set()

        for category_position, category_dto in enumerate(categories_dto):
            category = await self._resolve_category(uow, category_dto)
            if category.id in used_category_ids:
                raise ValidationError(
                    f"Duplicate category node for category_id={category.id}"
                )
            used_category_ids.add(category.id)
            categories.append(
                ResolvedCategory(
                    category=category,
                    dto=category_dto,
                    position=category_position,
                )
            )
            if self._is_new(category_dto):
                categories_to_create.append(category)

            for competency_dto in category_dto.competencies:
                competency = await self._resolve_competency(
                    uow,
                    competency_dto,
                    category_id=category.id,
                )
                if competency.id in used_competency_ids:
                    raise ValidationError(
                        f"Duplicate competency node for competency_id={competency.id}"
                    )
                used_competency_ids.add(competency.id)
                competencies.append(
                    ResolvedCompetency(
                        competency=competency,
                        dto=competency_dto,
                        category=category,
                        position=len(competencies),
                    )
                )
                if self._is_new(competency_dto):
                    competencies_to_create.append(competency)

                for sub_dto in competency_dto.sub_competencies:
                    sub_competency = await self._resolve_sub_competency(
                        uow,
                        sub_dto,
                        competency_id=competency.id,
                    )
                    if sub_competency.id in used_sub_competency_ids:
                        raise ValidationError(
                            "Duplicate sub-competency node for "
                            f"sub_competency_id={sub_competency.id}"
                        )
                    used_sub_competency_ids.add(sub_competency.id)
                    sub_competencies.append(
                        ResolvedSubCompetency(
                            sub_competency=sub_competency,
                            dto=sub_dto,
                            competency=competency,
                            position=len(sub_competencies),
                        )
                    )
                    if self._is_new(sub_dto):
                        sub_competencies_to_create.append(sub_competency)

        return ResolvedGraphPayload(
            categories_to_create=categories_to_create,
            competencies_to_create=competencies_to_create,
            sub_competencies_to_create=sub_competencies_to_create,
            categories=categories,
            competencies=competencies,
            sub_competencies=sub_competencies,
        )

    @staticmethod
    def _mode(dto: _GraphNodeDTO) -> str:
        mode = dto.mode
        if isinstance(mode, StrEnum):
            return mode.value
        return str(mode)

    @classmethod
    def _is_existing(cls, dto: _GraphNodeDTO) -> bool:
        return cls._mode(dto) == "existing"

    @classmethod
    def _is_new(cls, dto: _GraphNodeDTO) -> bool:
        return cls._mode(dto) == "new"

    async def _resolve_category(
        self, uow: UnitOfWork, category_dto: GraphCategoryDTO
    ) -> Category:
        if self._is_existing(category_dto):
            category_id = category_dto.id
            if category_id is None:
                raise ValidationError("Existing category requires id")
            category = await uow.categories.get(category_id)
            if category is None:
                raise NotFoundError(f"Category {category_id} not found")
            return category

        return Category(
            id=uuid4(),
            name=(category_dto.name or "").strip(),
            description=category_dto.description or "",
            emoji=category_dto.emoji or "",
        )

    async def _resolve_competency(
        self,
        uow: UnitOfWork,
        competency_dto: GraphCompetencyDTO,
        *,
        category_id: UUID,
    ) -> Competency:
        if self._is_existing(competency_dto):
            competency_id = competency_dto.id
            if competency_id is None:
                raise ValidationError("Existing competency requires id")
            competency = await uow.competencies.get(competency_id)
            if competency is None:
                raise NotFoundError(f"Competency {competency_id} not found")
            if competency.category_id != category_id:
                raise ValidationError(
                    "Existing competency does not belong to the selected category"
                )
            return competency

        return Competency(
            id=uuid4(),
            category_id=category_id,
            name=(competency_dto.name or "").strip(),
            description=competency_dto.description or "",
            sub_competencies=[],
        )

    async def _resolve_sub_competency(
        self,
        uow: UnitOfWork,
        sub_dto: GraphSubCompetencyDTO,
        *,
        competency_id: UUID,
    ) -> SubCompetency:
        if self._is_existing(sub_dto):
            sub_id = sub_dto.id
            if sub_id is None:
                raise ValidationError("Existing sub-competency requires id")
            sub_competency = await uow.sub_competencies.get(sub_id)
            if sub_competency is None:
                raise NotFoundError(f"Sub-competency {sub_id} not found")
            if sub_competency.competency_id != competency_id:
                raise ValidationError(
                    "Existing sub-competency does not belong to the selected competency"
                )
            return sub_competency

        return SubCompetency(
            id=uuid4(),
            competency_id=competency_id,
            name=(sub_dto.name or "").strip(),
            description=sub_dto.description or "",
            weight=sub_dto.weight,
            target_level=sub_dto.target_level,
        )
