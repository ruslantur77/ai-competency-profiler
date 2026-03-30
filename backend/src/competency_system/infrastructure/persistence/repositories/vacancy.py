from __future__ import annotations

from collections.abc import Collection, Sequence
from uuid import UUID

from sqlalchemy import delete, select

from competency_system.application.ports.repositories import VacancyInclude
from competency_system.domain.entities import Category, Competency, SubCompetency, Vacancy
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.infrastructure.persistence.mappers import vacancy_from_orm, vacancy_to_orm
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

type CategoryGraph = tuple[list[Category], list[Competency]]


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
            normalized = await self._load_normalized_graph(vacancy.id)
            if normalized is not None:
                vacancy.categories, vacancy.competencies = normalized
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
                normalized = await self._load_normalized_graph(vacancy.id)
                if normalized is not None:
                    vacancy.categories, vacancy.competencies = normalized
        return vacancies

    async def list_by_statuses(
        self,
        statuses: set[str] | None = None,
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
                normalized = await self._load_normalized_graph(vacancy.id)
                if normalized is not None:
                    vacancy.categories, vacancy.competencies = normalized
        return vacancies

    async def add(self, entity: Vacancy) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._upsert_canonical_graph(entity)
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

        if vacancy.categories:
            category_order = [category.id for category in vacancy.categories]
            competencies_source = [
                competency
                for category in vacancy.categories
                for competency in category.competencies
            ]
        else:
            seen: set[UUID] = set()
            category_order = []
            competencies_source = list(vacancy.competencies)
            for competency in competencies_source:
                if competency.category_id not in seen:
                    seen.add(competency.category_id)
                    category_order.append(competency.category_id)

        for category_position, category_id in enumerate(category_order):
            self._session.add(
                VacancyCategoryNodeOrm(
                    vacancy_id=vacancy.id,
                    category_id=category_id,
                    position=category_position,
                )
            )

        competency_position = 0
        sub_position = 0
        for competency in competencies_source:
            self._session.add(
                VacancyCompetencyNodeOrm(
                    vacancy_id=vacancy.id,
                    competency_id=competency.id,
                    category_id=competency.category_id,
                    is_required=competency.is_required,
                    position=competency_position,
                )
            )
            competency_position += 1

            for sub in competency.sub_competencies:
                self._session.add(
                    VacancySubCompetencyNodeOrm(
                        vacancy_id=vacancy.id,
                        sub_competency_id=sub.id,
                        competency_id=competency.id,
                        target_level=int(sub.target_level),
                        weight=sub.weight,
                        position=sub_position,
                    )
                )
                sub_position += 1
        await self._session.flush()

    async def _upsert_canonical_graph(self, vacancy: Vacancy) -> None:
        categories_by_id: dict[UUID, Category] = {
            category.id: category for category in vacancy.categories
        }
        competencies_source: list[Competency]
        if vacancy.categories:
            competencies_source = [
                competency
                for category in vacancy.categories
                for competency in category.competencies
            ]
        else:
            competencies_source = list(vacancy.competencies)

        for competency in competencies_source:
            if competency.category_id not in categories_by_id:
                categories_by_id[competency.category_id] = Category(
                    id=competency.category_id,
                    name=f"Category {competency.category_id}",
                    description="",
                    emoji="📋",
                    competencies=[],
                )

        for category in categories_by_id.values():
            await self._session.merge(
                CategoryOrm(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    emoji=category.emoji,
                )
            )

        for competency in competencies_source:
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

    async def _load_normalized_graph(
        self,
        vacancy_id: UUID,
    ) -> CategoryGraph | None:
        category_rows = (
            await self._session.scalars(
                select(VacancyCategoryNodeOrm)
                .where(VacancyCategoryNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancyCategoryNodeOrm.position)
            )
        ).all()
        if not category_rows:
            return None

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

        category_ids = [row.category_id for row in category_rows]
        competency_ids = [row.competency_id for row in competency_rows]
        sub_ids = [row.sub_competency_id for row in sub_rows]

        category_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(CategoryOrm).where(CategoryOrm.id.in_(category_ids))
                )
            ).all()
        }
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

        subs_by_competency: dict[UUID, list[SubCompetency]] = {}
        for sub_row in sub_rows:
            sub_model = sub_models.get(sub_row.sub_competency_id)
            if sub_model is None:
                continue
            subs_by_competency.setdefault(sub_row.competency_id, []).append(
                SubCompetency(
                    id=sub_model.id,
                    name=sub_model.name,
                    description=sub_model.description,
                    target_level=CompetencyLevel(sub_row.target_level),
                    weight=sub_row.weight,
                    created_at=sub_model.created_at,
                    updated_at=sub_model.updated_at,
                )
            )

        competencies_by_category: dict[UUID, list[Competency]] = {}
        all_competencies: list[Competency] = []
        for competency_row in competency_rows:
            competency_model = competency_models.get(competency_row.competency_id)
            if competency_model is None:
                continue
            competency = Competency(
                id=competency_model.id,
                category_id=competency_row.category_id,
                name=competency_model.name,
                description=competency_model.description,
                is_required=competency_row.is_required,
                sub_competencies=subs_by_competency.get(
                    competency_row.competency_id, []
                ),
                created_at=competency_model.created_at,
                updated_at=competency_model.updated_at,
            )
            competencies_by_category.setdefault(competency_row.category_id, []).append(
                competency
            )
            all_competencies.append(competency)

        categories: list[Category] = []
        for category_row in category_rows:
            category_model = category_models.get(category_row.category_id)
            if category_model is None:
                continue
            categories.append(
                Category(
                    id=category_model.id,
                    name=category_model.name,
                    description=category_model.description,
                    emoji=category_model.emoji,
                    competencies=competencies_by_category.get(
                        category_row.category_id, []
                    ),
                    created_at=category_model.created_at,
                    updated_at=category_model.updated_at,
                )
            )

        return categories, all_competencies
