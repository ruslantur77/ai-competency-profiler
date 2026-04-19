from __future__ import annotations

from collections.abc import Collection, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload, selectinload

from competency_system.application.ports.repositories import CandidateInclude
from competency_system.application.ports.repositories import (
    CandidateRepository as ICandidateRepository,
)
from competency_system.domain.entities import Candidate
from competency_system.infrastructure.persistence.mappers import (
    candidate_from_orm,
    candidate_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CandidateSubCompetencyAchievementOrm,
    VacancyOrm,
)
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
    normalize_include,
)


class CandidateRepository(
    SQLAlchemyRepository[Candidate, CandidateOrm, CandidateInclude],
    ICandidateRepository,
):
    model = CandidateOrm

    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[CandidateInclude] | None = None,
        include_deleted: bool = False,
    ) -> Candidate | None:
        statement = (
            select(self.model)
            .where(CandidateOrm.id == entity_id)
            .options(*self.load_options(include))
        )
        if not include_deleted:
            statement = statement.where(CandidateOrm.deleted_at.is_(None))
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    async def get_list(
        self,
        *,
        include: Collection[CandidateInclude] | None = None,
        limit: int | None = None,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> Sequence[Candidate]:
        statement = select(self.model).options(*self.load_options(include))
        if not include_deleted:
            statement = statement.where(CandidateOrm.deleted_at.is_(None))
        statement = statement.order_by(CandidateOrm.created_at.asc())
        if offset > 0:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        return [self.to_domain(row) for row in result.all()]

    def load_options(
        self,
        include: Collection[CandidateInclude] | None = None,
    ) -> Sequence[Any]:
        includes = normalize_include(include)
        options: list[Any] = []
        if CandidateInclude.ACHIEVEMENTS in includes:
            options.append(selectinload(CandidateOrm.achievements))
        if CandidateInclude.TEST_RESULTS in includes:
            options.append(selectinload(CandidateOrm.test_results))
        if (
            CandidateInclude.VACANCY in includes
            or CandidateInclude.VACANCY_SUBCOMPETENCIES in includes
        ):
            options.append(joinedload(CandidateOrm.vacancy))
        if CandidateInclude.VACANCY_SUBCOMPETENCIES in includes:
            options.append(
                joinedload(CandidateOrm.vacancy).selectinload(
                    VacancyOrm.competency_nodes
                )
            )
            options.append(
                joinedload(CandidateOrm.vacancy).selectinload(
                    VacancyOrm.sub_competency_nodes
                )
            )
        return tuple(options)

    async def get_by_external_id(
        self,
        external_id: str,
        *,
        include: Collection[CandidateInclude] | None = None,
        include_deleted: bool = False,
    ) -> Candidate | None:
        statement = (
            select(self.model)
            .where(CandidateOrm.external_id == external_id)
            .options(*self.load_options(include))
        )
        if not include_deleted:
            statement = statement.where(CandidateOrm.deleted_at.is_(None))
        model = await self._session.scalar(statement)
        if model is None:
            return None
        candidate = self.to_domain(model)
        return candidate

    async def list_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: Collection[CandidateInclude] | None = None,
        include_deleted: bool = False,
    ) -> Sequence[Candidate]:
        statement = (
            select(CandidateOrm)
            .where(CandidateOrm.vacancy_id == vacancy_id)
            .order_by(CandidateOrm.created_at.asc())
            .options(*self.load_options(include))
        )
        if not include_deleted:
            statement = statement.where(CandidateOrm.deleted_at.is_(None))
        result = await self._session.scalars(statement)
        rows = result.all()
        candidates: list[Candidate] = [self.to_domain(row) for row in rows]
        return candidates

    async def add(self, entity: Candidate) -> None:
        await super().add(entity=entity)

        await self._session.execute(
            delete(CandidateSubCompetencyAchievementOrm).where(
                CandidateSubCompetencyAchievementOrm.candidate_id == entity.id
            )
        )
        sub_ids = {item.sub_competency_id for item in entity.achievements}

        for sub_id in sorted(sub_ids, key=str):
            self._session.add(
                CandidateSubCompetencyAchievementOrm(
                    candidate_id=entity.id,
                    sub_competency_id=sub_id,
                )
            )
        await self._session.flush()

    async def soft_delete(self, entity_id: UUID) -> Candidate | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        if model.deleted_at is None:
            model.deleted_at = datetime.now(UTC)
            await self._session.flush()
        return self.to_domain(model)

    def to_domain(self, model: CandidateOrm) -> Candidate:
        return candidate_from_orm(model)

    def to_model(self, entity: Candidate) -> CandidateOrm:
        return candidate_to_orm(entity)
