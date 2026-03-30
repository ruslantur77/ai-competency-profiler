from __future__ import annotations

from uuid import UUID

from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
)
from competency_system.domain.value_objects.enums import VacancyStatus


def build_taxonomy() -> tuple[Category, Competency, SubCompetency, SubCompetency]:
    sub1 = SubCompetency(name="REST", description="REST APIs", weight=0.6)
    sub2 = SubCompetency(name="SQL", description="PostgreSQL", weight=0.4)
    competency = Competency(
        category_id=UUID(int=0),
        name="Backend",
        description="Core backend",
        sub_competencies=[sub1, sub2],
        is_required=True,
    )
    category = Category(
        name="Engineering",
        description="Engineering skills",
        competencies=[competency],
    )
    competency.category_id = category.id
    return category, competency, sub1, sub2


def build_vacancy_with_graph() -> tuple[
    Vacancy,
    Category,
    Competency,
    SubCompetency,
    SubCompetency,
]:
    category, competency, sub1, sub2 = build_taxonomy()
    vacancy = Vacancy(
        name="Backend Engineer",
        description="Build APIs",
        status=VacancyStatus.READY,
        categories=[category],
        competencies=[competency],
    )
    return vacancy, category, competency, sub1, sub2
