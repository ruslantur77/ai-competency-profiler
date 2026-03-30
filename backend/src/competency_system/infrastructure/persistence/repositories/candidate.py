from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from competency_system.application.ports.repositories import CandidateInclude
from competency_system.domain.entities import Candidate
from competency_system.infrastructure.persistence.mappers import candidate_from_orm, candidate_to_orm
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CandidateSubCompetencyAchievementOrm,
)
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
    normalize_include,
)


class CandidateRepository(
    SQLAlchemyRepository[Candidate, CandidateOrm],
):
    model = CandidateOrm

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
        return tuple(options)

    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[CandidateInclude] | None = None,
    ) -> Candidate | None:
        model = await self._session.get(
            self.model,
            entity_id,
            options=list(self.load_options(include)),
        )
        if model is None:
            return None
        candidate = self.to_domain(model)
        includes = normalize_include(include)
        if CandidateInclude.ACHIEVEMENTS in includes:
            candidate.achieved_subcompetency_ids = {
                row.sub_competency_id for row in model.achievements
            }
        return candidate

    async def get_by_external_id(
        self,
        external_id: str,
        *,
        include: Collection[CandidateInclude] | None = None,
    ) -> Candidate | None:
        statement = (
            select(self.model)
            .where(CandidateOrm.external_id == external_id)
            .options(*self.load_options(include))
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        candidate = self.to_domain(model)
        includes = normalize_include(include)
        if CandidateInclude.ACHIEVEMENTS in includes:
            candidate.achieved_subcompetency_ids = {
                row.sub_competency_id for row in model.achievements
            }
        return candidate

    async def list_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: Collection[CandidateInclude] | None = None,
    ) -> Sequence[Candidate]:
        statement = (
            select(CandidateOrm)
            .where(CandidateOrm.vacancy_id == vacancy_id)
            .order_by(CandidateOrm.created_at.asc())
            .options(*self.load_options(include))
        )
        result = await self._session.scalars(statement)
        rows = result.all()
        includes = normalize_include(include)
        candidates: list[Candidate] = []
        for row in rows:
            candidate = self.to_domain(row)
            if CandidateInclude.ACHIEVEMENTS in includes:
                candidate.achieved_subcompetency_ids = {
                    item.sub_competency_id for item in row.achievements
                }
            candidates.append(candidate)
        return candidates

    async def add(self, entity: Candidate) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

        await self._session.execute(
            delete(CandidateSubCompetencyAchievementOrm).where(
                CandidateSubCompetencyAchievementOrm.candidate_id == entity.id
            )
        )
        for sub_id in sorted(entity.achieved_subcompetency_ids, key=str):
            self._session.add(
                CandidateSubCompetencyAchievementOrm(
                    candidate_id=entity.id,
                    sub_competency_id=sub_id,
                )
            )
        await self._session.flush()

    def to_domain(self, model: CandidateOrm) -> Candidate:
        return candidate_from_orm(model)

    def to_model(self, entity: Candidate) -> CandidateOrm:
        return candidate_to_orm(entity)
