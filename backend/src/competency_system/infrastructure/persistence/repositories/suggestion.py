from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from competency_system.domain.entities import VacancyGraphSuggestion
from competency_system.infrastructure.persistence.mappers import (
    vacancy_suggestion_from_orm,
    vacancy_suggestion_to_orm,
)
from competency_system.infrastructure.persistence.models import VacancySuggestionOrm
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
)


class VacancySuggestionRepository(
    SQLAlchemyRepository[VacancyGraphSuggestion, VacancySuggestionOrm],
):
    model = VacancySuggestionOrm

    async def list_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: object | None = None,
    ) -> Sequence[VacancyGraphSuggestion]:
        statement = (
            select(self.model)
            .where(VacancySuggestionOrm.vacancy_id == vacancy_id)
            .order_by(VacancySuggestionOrm.created_at)
        )
        result = await self._session.scalars(statement)
        return [self.to_domain(model) for model in result.all()]

    def to_domain(self, model: VacancySuggestionOrm) -> VacancyGraphSuggestion:
        return vacancy_suggestion_from_orm(model)

    def to_model(self, entity: VacancyGraphSuggestion) -> VacancySuggestionOrm:
        return vacancy_suggestion_to_orm(entity)
