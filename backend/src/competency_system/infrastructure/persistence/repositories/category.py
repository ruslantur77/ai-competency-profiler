from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy.orm import selectinload

from competency_system.application.ports.repositories import (
    CategoryInclude,
    CompetencyInclude,
)
from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.infrastructure.persistence.mappers import (
    category_from_orm,
    category_to_orm,
    competency_from_orm,
    competency_to_orm,
    subcompetency_from_orm,
    subcompetency_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    CategoryOrm,
    CompetencyOrm,
    SubCompetencyOrm,
)
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
    normalize_include,
)


class CategoryRepository(SQLAlchemyRepository[Category, CategoryOrm]):
    model = CategoryOrm

    def load_options(
        self,
        include: Collection[CategoryInclude] | None = None,
    ) -> Sequence[Any]:
        includes = normalize_include(include)
        if CategoryInclude.SUB_COMPETENCIES in includes:
            return (
                selectinload(CategoryOrm.competencies).selectinload(
                    CompetencyOrm.sub_competencies
                ),
            )
        if CategoryInclude.COMPETENCIES in includes:
            return (selectinload(CategoryOrm.competencies),)
        return ()

    def to_domain(self, model: CategoryOrm) -> Category:
        return category_from_orm(model)

    def to_model(self, entity: Category) -> CategoryOrm:
        return category_to_orm(entity)


class CompetencyRepository(SQLAlchemyRepository[Competency, CompetencyOrm]):
    model = CompetencyOrm

    def load_options(
        self,
        include: Collection[CompetencyInclude] | None = None,
    ) -> Sequence[Any]:
        includes = normalize_include(include)
        options: list[Any] = []
        if CompetencyInclude.CATEGORY in includes:
            options.append(selectinload(CompetencyOrm.category))
        if CompetencyInclude.SUB_COMPETENCIES in includes:
            options.append(selectinload(CompetencyOrm.sub_competencies))
        return tuple(options)

    def to_domain(self, model: CompetencyOrm) -> Competency:
        return competency_from_orm(model)

    def to_model(self, entity: Competency) -> CompetencyOrm:
        return competency_to_orm(entity)


class SubCompetencyRepository(
    SQLAlchemyRepository[SubCompetency, SubCompetencyOrm],
):
    model = SubCompetencyOrm

    def to_domain(self, model: SubCompetencyOrm) -> SubCompetency:
        return subcompetency_from_orm(model)

    def to_model(self, entity: SubCompetency) -> SubCompetencyOrm:
        return subcompetency_to_orm(entity)
