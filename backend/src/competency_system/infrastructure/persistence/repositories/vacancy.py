from __future__ import annotations

from collections.abc import Collection, Sequence
from uuid import UUID

from sqlalchemy import delete, select

from competency_system.application.ports.repositories import VacancyInclude
from competency_system.domain.entities import (
    Competency,
    SubCompetency,
    Vacancy,
    VacancyCategoryNode,
    VacancyCompetencyNode,
    VacancySubCompetencyNode,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.infrastructure.persistence.mappers import vacancy_from_orm, vacancy_to_orm
from competency_system.infrastructure.persistence.models import (
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


class VacancyRepository(SQLAlchemyRepository[Vacancy, VacancyOrm]):
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
                vacancy.competencies,
            ) = await self._load_normalized_graph(vacancy.id)
        return vacancy

    async def list(
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
                    vacancy.competencies,
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
                    vacancy.competencies,
                ) = await self._load_normalized_graph(vacancy.id)
        return vacancies

    async def add(self, entity: Vacancy) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

        if (
            not entity.category_nodes
            and not entity.competency_nodes
            and not entity.sub_competency_nodes
            and entity.competencies
        ):
            entity.category_nodes, entity.competency_nodes, entity.sub_competency_nodes = (
                self._build_nodes_from_competencies(entity)
            )

        await self._upsert_canonical_competencies(entity.competencies)
        await self._replace_normalized_graph(entity)

    def to_domain(self, model: VacancyOrm) -> Vacancy:
        return vacancy_from_orm(model)

    def to_model(self, entity: Vacancy) -> VacancyOrm:
        return vacancy_to_orm(entity)

    def _build_nodes_from_competencies(
        self,
        vacancy: Vacancy,
    ) -> tuple[
        list[VacancyCategoryNode],
        list[VacancyCompetencyNode],
        list[VacancySubCompetencyNode],
    ]:
        category_order: list[UUID] = []
        seen_categories: set[UUID] = set()
        for competency in vacancy.competencies:
            if competency.category_id in seen_categories:
                continue
            seen_categories.add(competency.category_id)
            category_order.append(competency.category_id)

        category_nodes = [
            VacancyCategoryNode(
                vacancy_id=vacancy.id,
                category_id=category_id,
                position=position,
            )
            for position, category_id in enumerate(category_order)
        ]

        competency_nodes: list[VacancyCompetencyNode] = []
        sub_nodes: list[VacancySubCompetencyNode] = []
        for competency_position, competency in enumerate(vacancy.competencies):
            competency_nodes.append(
                VacancyCompetencyNode(
                    vacancy_id=vacancy.id,
                    competency_id=competency.id,
                    category_id=competency.category_id,
                    is_required=competency.is_required,
                    position=competency_position,
                )
            )
            for sub_position, sub in enumerate(competency.sub_competencies):
                sub_nodes.append(
                    VacancySubCompetencyNode(
                        vacancy_id=vacancy.id,
                        sub_competency_id=sub.id,
                        competency_id=competency.id,
                        target_level=sub.target_level,
                        weight=sub.weight,
                        position=len(sub_nodes),
                    )
                )
        return category_nodes, competency_nodes, sub_nodes

    async def _upsert_canonical_competencies(
        self,
        competencies: list[Competency],
    ) -> None:
        for competency in competencies:
            await self._session.merge(
                CompetencyOrm(
                    id=competency.id,
                    category_id=competency.category_id,
                    name=competency.name,
                    description=competency.description,
                )
            )
            for sub in competency.sub_competencies:
                await self._session.merge(
                    SubCompetencyOrm(
                        id=sub.id,
                        competency_id=competency.id,
                        name=sub.name,
                        description=sub.description,
                    )
                )

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
        list[Competency],
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
                    target_level=CompetencyLevel(row.target_level),
                    weight=row.weight,
                    created_at=sub_model.created_at,
                    updated_at=sub_model.updated_at,
                )
            )

        competencies: list[Competency] = []
        for row in competency_rows:
            model = competency_models.get(row.competency_id)
            if model is None:
                continue
            competencies.append(
                Competency(
                    id=model.id,
                    category_id=row.category_id,
                    name=model.name,
                    description=model.description,
                    is_required=row.is_required,
                    sub_competencies=sub_by_competency.get(row.competency_id, []),
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
            )

        category_nodes = [
            VacancyCategoryNode(
                id=row.id,
                vacancy_id=row.vacancy_id,
                category_id=row.category_id,
                position=row.position,
                created_at=row.created_at,
                updated_at=row.updated_at,
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
            )
            for row in sub_rows
        ]
        return category_nodes, competency_nodes, sub_nodes, competencies
