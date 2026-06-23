from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
    VacancyCategoryNode,
    VacancyCompetencyNode,
    VacancyGraphSuggestion,
    VacancySubCompetencyNode,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import SuggestionStage


class VacancySuggestionApprovalHelper:
    @staticmethod
    def _next_position(nodes: Sequence[object]) -> int:
        if not nodes:
            return 0
        return max(getattr(node, "position", 0) for node in nodes) + 1

    async def _apply_approved_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        if suggestion.stage == SuggestionStage.CATEGORY:
            await self._apply_category_suggestion(uow, vacancy, suggestion)
            return
        if suggestion.stage == SuggestionStage.COMPETENCY:
            await self._apply_competency_suggestion(uow, vacancy, suggestion)
            return
        await self._apply_sub_competency_suggestion(uow, vacancy, suggestion)

    async def _apply_category_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        category = Category(
            id=uuid4(),
            name=suggestion.name,
            description=suggestion.description,
            emoji="",
        )
        await uow.categories.add(category)
        self._ensure_category_node(vacancy, category.id)

    async def _apply_competency_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        parent_category_id = suggestion.parent_category_id
        if parent_category_id is None:
            raise ValidationError("Competency suggestion is missing parent_category_id")
        parent_category = await uow.categories.get(parent_category_id)
        if parent_category is None:
            raise NotFoundError(f"Parent category {parent_category_id} not found")

        competency = Competency(
            id=uuid4(),
            category_id=parent_category.id,
            name=suggestion.name,
            description=suggestion.description,
            sub_competencies=[],
        )
        await uow.competencies.add(competency)

        self._ensure_category_node(vacancy, parent_category.id)
        self._ensure_competency_node(
            vacancy,
            competency.id,
            parent_category.id,
            is_required=suggestion.is_required
            if suggestion.is_required is not None
            else True,
        )

    async def _apply_sub_competency_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        parent_competency_id = suggestion.parent_competency_id
        if parent_competency_id is None:
            raise ValidationError(
                "Sub-competency suggestion is missing parent_competency_id"
            )
        parent_competency = await uow.competencies.get(parent_competency_id)
        if parent_competency is None:
            raise NotFoundError(f"Parent competency {parent_competency_id} not found")

        target_level = suggestion.target_level or CompetencyLevel.BEGINNER
        weight = suggestion.weight if suggestion.weight is not None else 1.0
        sub_competency = SubCompetency(
            id=uuid4(),
            competency_id=parent_competency.id,
            name=suggestion.name,
            description=suggestion.description,
            weight=weight,
            target_level=target_level,
        )
        await uow.sub_competencies.add(sub_competency)

        self._ensure_category_node(vacancy, parent_competency.category_id)
        self._ensure_competency_node(
            vacancy,
            parent_competency.id,
            parent_competency.category_id,
            is_required=True,
        )
        self._ensure_sub_competency_node(
            vacancy,
            sub_competency.id,
            parent_competency.id,
            target_level=target_level,
            weight=weight,
        )

    def _ensure_category_node(self, vacancy: Vacancy, category_id: UUID) -> None:
        if any(node.category_id == category_id for node in vacancy.category_nodes):
            return
        vacancy.category_nodes.append(
            VacancyCategoryNode(
                id=uuid4(),
                vacancy_id=vacancy.id,
                category_id=category_id,
                position=self._next_position(vacancy.category_nodes),
            )
        )

    def _ensure_competency_node(
        self,
        vacancy: Vacancy,
        competency_id: UUID,
        category_id: UUID,
        *,
        is_required: bool,
    ) -> None:
        if any(
            node.competency_id == competency_id for node in vacancy.competency_nodes
        ):
            return
        vacancy.competency_nodes.append(
            VacancyCompetencyNode(
                id=uuid4(),
                vacancy_id=vacancy.id,
                competency_id=competency_id,
                category_id=category_id,
                is_required=is_required,
                position=self._next_position(vacancy.competency_nodes),
            )
        )

    def _ensure_sub_competency_node(
        self,
        vacancy: Vacancy,
        sub_competency_id: UUID,
        competency_id: UUID,
        *,
        target_level: CompetencyLevel,
        weight: float,
    ) -> None:
        if any(
            node.sub_competency_id == sub_competency_id
            for node in vacancy.sub_competency_nodes
        ):
            return
        vacancy.sub_competency_nodes.append(
            VacancySubCompetencyNode(
                id=uuid4(),
                vacancy_id=vacancy.id,
                sub_competency_id=sub_competency_id,
                competency_id=competency_id,
                target_level=target_level,
                weight=weight,
                position=self._next_position(vacancy.sub_competency_nodes),
            )
        )
