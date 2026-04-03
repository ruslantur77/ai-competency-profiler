from __future__ import annotations

from collections.abc import Collection, Sequence
from uuid import UUID

from sqlalchemy import delete, select

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
    ) -> Vacancy | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
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
    ) -> Sequence[Vacancy]:
        statement = select(self.model).order_by(VacancyOrm.created_at.desc())
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
    ) -> Sequence[Vacancy]:
        statement = select(self.model).order_by(VacancyOrm.created_at.desc())
        if statuses:
            statement = statement.where(VacancyOrm.status.in_(statuses))
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

        for node in vacancy.category_nodes:
            self._session.add(
                VacancyCategoryNodeOrm(
                    id=node.id,
                    vacancy_id=vacancy.id,
                    category_id=node.category_id,
                    position=node.position,
                )
            )

        for node in vacancy.competency_nodes:
            self._session.add(
                VacancyCompetencyNodeOrm(
                    id=node.id,
                    vacancy_id=vacancy.id,
                    competency_id=node.competency_id,
                    category_id=node.category_id,
                    is_required=node.is_required,
                    position=node.position,
                )
            )

        for node in vacancy.sub_competency_nodes:
            self._session.add(
                VacancySubCompetencyNodeOrm(
                    id=node.id,
                    vacancy_id=vacancy.id,
                    sub_competency_id=node.sub_competency_id,
                    competency_id=node.competency_id,
                    target_level=int(node.target_level),
                    weight=node.weight,
                    position=node.position,
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
        category_rows = (
            await self._session.scalars(
                select(VacancyCategoryNodeOrm)
                .where(VacancyCategoryNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancyCategoryNodeOrm.position)
            )
        ).all()
        competency_rows = (
            await self._session.scalars(
                select(VacancyCompetencyNodeOrm)
                .where(VacancyCompetencyNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancyCompetencyNodeOrm.position)
            )
        ).all()
        sub_rows = (
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
        for row in sub_rows:
            sub_model = sub_models.get(row.sub_competency_id)
            if sub_model is None:
                continue
            sub_by_competency.setdefault(row.competency_id, []).append(
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
        for row in competency_rows:
            model = competency_models.get(row.competency_id)
            if model is None:
                continue
            competencies[row.competency_id] = Competency(
                id=model.id,
                category_id=row.category_id,
                name=model.name,
                description=model.description,
                sub_competencies=sub_by_competency.get(row.competency_id, []),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
        categories: dict[UUID, Category] = {}
        for row in category_rows:
            model = category_models.get(row.category_id)
            if model is None:
                continue
            categories[row.category_id] = Category(
                id=model.id,
                name=model.name,
                description=model.description,
                emoji=model.emoji,
                created_at=model.created_at,
                updated_at=model.updated_at,
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
