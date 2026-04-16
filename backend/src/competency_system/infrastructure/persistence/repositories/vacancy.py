from __future__ import annotations

from collections.abc import Collection, Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select

from competency_system.application.ports.repositories import VacancyInclude
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
    VacancyCategoryNode,
    VacancyCompetencyNode,
    VacancySubCompetencyNode,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.infrastructure.persistence.mappers import (
    vacancy_from_orm,
    vacancy_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    CategoryOrm,
    CompetencyOrm,
    SubCompetencyOrm,
    VacancyCategoryNodeOrm,
    VacancyCompetencyNodeOrm,
    VacancyOrm,
    VacancySubCompetencyNodeOrm,
)
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
    normalize_include,
)


class VacancyRepository(
    SQLAlchemyRepository[Vacancy, VacancyOrm, VacancyInclude],
):
    model = VacancyOrm

    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[VacancyInclude] | None = None,
        include_deleted: bool = False,
    ) -> Vacancy | None:
        model = await self._session.get(self.model, entity_id)
        if model is None or (model.deleted_at is not None and not include_deleted):
            return None
        vacancy = self.to_domain(model)
        includes = normalize_include(include)
        if VacancyInclude.NORMALIZED_GRAPH in includes:
            (
                vacancy.category_nodes,
                vacancy.competency_nodes,
                vacancy.sub_competency_nodes,
            ) = await self._load_normalized_graph(vacancy.id)
        return vacancy

    async def get_list(
        self,
        *,
        include: Collection[VacancyInclude] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[Vacancy]:
        statement = (
            select(self.model)
            .where(VacancyOrm.deleted_at.is_(None))
            .order_by(VacancyOrm.created_at.desc())
        )
        if offset > 0:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        vacancies = [self.to_domain(model) for model in result.all()]
        includes = normalize_include(include)
        if VacancyInclude.NORMALIZED_GRAPH in includes:
            for vacancy in vacancies:
                (
                    vacancy.category_nodes,
                    vacancy.competency_nodes,
                    vacancy.sub_competency_nodes,
                ) = await self._load_normalized_graph(vacancy.id)
        return vacancies

    async def list_by_statuses(
        self,
        statuses: set[VacancyStatus] | None = None,
        *,
        include: Collection[VacancyInclude] | None = None,
        limit: int | None = None,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> Sequence[Vacancy]:
        statement = select(self.model).order_by(VacancyOrm.created_at.desc())
        if not include_deleted:
            statement = statement.where(VacancyOrm.deleted_at.is_(None))
        if statuses:
            statement = statement.where(VacancyOrm.status.in_(statuses))
        if offset > 0:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        vacancies = [self.to_domain(model) for model in result.all()]
        includes = normalize_include(include)
        if VacancyInclude.NORMALIZED_GRAPH in includes:
            for vacancy in vacancies:
                (
                    vacancy.category_nodes,
                    vacancy.competency_nodes,
                    vacancy.sub_competency_nodes,
                ) = await self._load_normalized_graph(vacancy.id)
        return vacancies

    async def count_by_statuses(
        self,
        statuses: set[VacancyStatus] | None = None,
        *,
        include_deleted: bool = False,
    ) -> int:
        statement = select(func.count()).select_from(VacancyOrm)
        if not include_deleted:
            statement = statement.where(VacancyOrm.deleted_at.is_(None))
        if statuses:
            statement = statement.where(VacancyOrm.status.in_(statuses))
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def soft_delete(self, entity_id: UUID) -> Vacancy | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        if model.deleted_at is None:
            model.deleted_at = datetime.now(UTC)
            await self._session.flush()
        return self.to_domain(model)

    async def restore(self, entity_id: UUID) -> Vacancy | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        model.deleted_at = None
        await self._session.flush()
        return self.to_domain(model)

    async def hard_delete(self, entity_id: UUID) -> None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()

    async def add(self, entity: Vacancy) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()
        await self._replace_normalized_graph(entity)

    def to_domain(self, model: VacancyOrm) -> Vacancy:
        return vacancy_from_orm(model)

    def to_model(self, entity: Vacancy) -> VacancyOrm:
        return vacancy_to_orm(entity)

    async def _replace_normalized_graph(self, vacancy: Vacancy) -> None:
        await self._session.execute(
            delete(VacancySubCompetencyNodeOrm).where(
                VacancySubCompetencyNodeOrm.vacancy_id == vacancy.id
            )
        )
        await self._session.execute(
            delete(VacancyCompetencyNodeOrm).where(
                VacancyCompetencyNodeOrm.vacancy_id == vacancy.id
            )
        )
        await self._session.execute(
            delete(VacancyCategoryNodeOrm).where(
                VacancyCategoryNodeOrm.vacancy_id == vacancy.id
            )
        )

        for node_cat in vacancy.category_nodes:
            self._session.add(
                VacancyCategoryNodeOrm(
                    id=node_cat.id,
                    vacancy_id=vacancy.id,
                    category_id=node_cat.category_id,
                    position=node_cat.position,
                )
            )

        for node_comp in vacancy.competency_nodes:
            self._session.add(
                VacancyCompetencyNodeOrm(
                    id=node_comp.id,
                    vacancy_id=vacancy.id,
                    competency_id=node_comp.competency_id,
                    category_id=node_comp.category_id,
                    is_required=node_comp.is_required,
                    position=node_comp.position,
                )
            )

        for node_sub in vacancy.sub_competency_nodes:
            self._session.add(
                VacancySubCompetencyNodeOrm(
                    id=node_sub.id,
                    vacancy_id=vacancy.id,
                    sub_competency_id=node_sub.sub_competency_id,
                    competency_id=node_sub.competency_id,
                    target_level=int(node_sub.target_level),
                    weight=node_sub.weight,
                    position=node_sub.position,
                )
            )

        await self._session.flush()

    async def _load_normalized_graph(
        self,
        vacancy_id: UUID,
    ) -> tuple[
        list[VacancyCategoryNode],
        list[VacancyCompetencyNode],
        list[VacancySubCompetencyNode],
    ]:
        category_rows: Sequence[VacancyCategoryNodeOrm] = (
            await self._session.scalars(
                select(VacancyCategoryNodeOrm)
                .where(VacancyCategoryNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancyCategoryNodeOrm.position)
            )
        ).all()
        competency_rows: Sequence[VacancyCompetencyNodeOrm] = (
            await self._session.scalars(
                select(VacancyCompetencyNodeOrm)
                .where(VacancyCompetencyNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancyCompetencyNodeOrm.position)
            )
        ).all()
        sub_rows: Sequence[VacancySubCompetencyNodeOrm] = (
            await self._session.scalars(
                select(VacancySubCompetencyNodeOrm)
                .where(VacancySubCompetencyNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancySubCompetencyNodeOrm.position)
            )
        ).all()

        competency_ids = [row.competency_id for row in competency_rows]
        sub_ids = [row.sub_competency_id for row in sub_rows]
        category_ids = [row.category_id for row in category_rows]

        competency_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(CompetencyOrm).where(CompetencyOrm.id.in_(competency_ids))
                )
            ).all()
        }
        sub_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(SubCompetencyOrm).where(SubCompetencyOrm.id.in_(sub_ids))
                )
            ).all()
        }
        category_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(CategoryOrm).where(CategoryOrm.id.in_(category_ids))
                )
            ).all()
        }

        sub_by_competency: dict[UUID, list[SubCompetency]] = {}
        for row_sub in sub_rows:
            sub_model = sub_models.get(row_sub.sub_competency_id)
            if sub_model is None:
                continue
            sub_by_competency.setdefault(row_sub.competency_id, []).append(
                SubCompetency(
                    id=sub_model.id,
                    competency_id=sub_model.competency_id,
                    name=sub_model.name,
                    description=sub_model.description,
                    weight=sub_model.weight,
                    created_at=sub_model.created_at,
                    updated_at=sub_model.updated_at,
                )
            )

        competencies: dict[UUID, Competency] = {}
        for row_comp in competency_rows:
            model = competency_models.get(row_comp.competency_id)
            if model is None:
                continue
            competencies[row_comp.competency_id] = Competency(
                id=model.id,
                category_id=row_comp.category_id,
                name=model.name,
                description=model.description,
                sub_competencies=sub_by_competency.get(row_comp.competency_id, []),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
        categories: dict[UUID, Category] = {}
        for row_cat in category_rows:
            model_cat = category_models.get(row_cat.category_id)
            if model_cat is None:
                continue
            categories[row_cat.category_id] = Category(
                id=model_cat.id,
                name=model_cat.name,
                description=model_cat.description,
                emoji=model_cat.emoji,
                created_at=model_cat.created_at,
                updated_at=model_cat.updated_at,
            )

        category_nodes = [
            VacancyCategoryNode(
                id=row.id,
                vacancy_id=row.vacancy_id,
                category_id=row.category_id,
                position=row.position,
                created_at=row.created_at,
                updated_at=row.updated_at,
                category=categories.get(row.category_id),
            )
            for row in category_rows
        ]
        competency_nodes = [
            VacancyCompetencyNode(
                id=row.id,
                vacancy_id=row.vacancy_id,
                competency_id=row.competency_id,
                category_id=row.category_id,
                is_required=row.is_required,
                position=row.position,
                created_at=row.created_at,
                updated_at=row.updated_at,
                category=categories.get(row.category_id),
                competency=competencies.get(row.competency_id),
            )
            for row in competency_rows
        ]
        sub_nodes = [
            VacancySubCompetencyNode(
                id=row.id,
                vacancy_id=row.vacancy_id,
                sub_competency_id=row.sub_competency_id,
                competency_id=row.competency_id,
                target_level=CompetencyLevel(row.target_level),
                weight=row.weight,
                position=row.position,
                created_at=row.created_at,
                updated_at=row.updated_at,
                competency=competencies.get(row.competency_id),
                sub_competency=next(
                    (
                        sub
                        for sub in sub_by_competency.get(row.competency_id, [])
                        if sub.id == row.sub_competency_id
                    ),
                    None,
                ),
            )
            for row in sub_rows
        ]
        return category_nodes, competency_nodes, sub_nodes
