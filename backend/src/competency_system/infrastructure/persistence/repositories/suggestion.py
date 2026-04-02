from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from competency_system.application.ports.repositories import (
    VacancyGraphSuggestionInclude,
)
from competency_system.application.ports.repositories import (
    VacancySuggestionRepository as IVacancySuggestionRepository,
)
from competency_system.domain.entities import VacancyGraphSuggestion
from competency_system.infrastructure.persistence.mappers import (
    vacancy_suggestion_from_orm,
    vacancy_suggestion_to_orm,
)
from competency_system.infrastructure.persistence.models import VacancySuggestionOrm
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
    normalize_include,
)


class VacancySuggestionRepository(
    SQLAlchemyRepository[
        VacancyGraphSuggestion, VacancySuggestionOrm, VacancyGraphSuggestionInclude
    ],
    IVacancySuggestionRepository,
):
    model = VacancySuggestionOrm

    def load_options(
        self, include: Collection[VacancyGraphSuggestionInclude] | None = None
    ) -> Sequence[Any]:
        includes = normalize_include(include)
        options: list[Any] = []
        if VacancyGraphSuggestionInclude.PARENT_CATEGORY in includes:
            options.append(selectinload(VacancySuggestionOrm.parent_category))
        if VacancyGraphSuggestionInclude.PARENT_COMPETENCY in includes:
            options.append(selectinload(VacancySuggestionOrm.parent_competency))
        if VacancyGraphSuggestionInclude.VACANCY in includes:
            options.append(selectinload(VacancySuggestionOrm.vacancy))

        return tuple(options)

    async def list_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: Collection[VacancyGraphSuggestionInclude] | None = None,
    ) -> Sequence[VacancyGraphSuggestion]:
        statement = (
            select(self.model)
            .where(VacancySuggestionOrm.vacancy_id == vacancy_id)
            .order_by(VacancySuggestionOrm.created_at)
            .options(*self.load_options(include))
        )
        result = await self._session.scalars(statement)
        return [self.to_domain(model) for model in result.all()]

    def to_domain(self, model: VacancySuggestionOrm) -> VacancyGraphSuggestion:
        return vacancy_suggestion_from_orm(model)

    def to_model(self, entity: VacancyGraphSuggestion) -> VacancySuggestionOrm:
        return vacancy_suggestion_to_orm(entity)
