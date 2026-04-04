from __future__ import annotations

from uuid import UUID

from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import (
    CategoryFactory,
    CompetencyFactory,
    SubCompetencyFactory,
    VacancyCategoryNodeFactory,
    VacancyCompetencyNodeFactory,
    VacancyFactory,
    VacancySubCompetencyNodeFactory,
)


def build_taxonomy() -> tuple[Category, Competency, SubCompetency, SubCompetency]:
    category = CategoryFactory().make(
        {
            "name": "Engineering",
            "description": "Engineering skills",
            "competencies": [],
        }
    )
    competency = CompetencyFactory().make(
        {
            "category_id": category.id,
            "name": "Backend",
            "description": "Core backend",
            "sub_competencies": [],
            "category": category,
        }
    )
    sub1 = SubCompetencyFactory().make(
        {
            "competency_id": competency.id,
            "name": "REST",
            "description": "REST APIs",
            "weight": 0.6,
            "competency": competency,
        }
    )
    sub2 = SubCompetencyFactory().make(
        {
            "competency_id": competency.id,
            "name": "SQL",
            "description": "PostgreSQL",
            "weight": 0.4,
            "competency": competency,
        }
    )

    competency.sub_competencies = [sub1, sub2]
    category.competencies = [competency]
    return category, competency, sub1, sub2


def build_vacancy_with_graph() -> tuple[
    Vacancy,
    Category,
    Competency,
    SubCompetency,
    SubCompetency,
]:
    category, competency, sub1, sub2 = build_taxonomy()
    vacancy = VacancyFactory().make(
        {
            "name": "Backend Engineer",
            "description": "Build APIs",
            "status": VacancyStatus.READY,
            "category_nodes": [
                VacancyCategoryNodeFactory().make(
                    {
                        "vacancy_id": UUID(int=0),
                        "category_id": category.id,
                        "position": 0,
                        "category": category,
                    }
                )
            ],
            "competency_nodes": [
                VacancyCompetencyNodeFactory().make(
                    {
                        "vacancy_id": UUID(int=0),
                        "competency_id": competency.id,
                        "category_id": category.id,
                        "is_required": True,
                        "position": 0,
                        "category": category,
                        "competency": competency,
                    }
                )
            ],
            "sub_competency_nodes": [
                VacancySubCompetencyNodeFactory().make(
                    {
                        "vacancy_id": UUID(int=0),
                        "sub_competency_id": sub1.id,
                        "competency_id": competency.id,
                        "target_level": CompetencyLevel.ADVANCED,
                        "weight": 0.6,
                        "position": 0,
                        "competency": competency,
                        "sub_competency": sub1,
                    }
                ),
                VacancySubCompetencyNodeFactory().make(
                    {
                        "vacancy_id": UUID(int=0),
                        "sub_competency_id": sub2.id,
                        "competency_id": competency.id,
                        "target_level": CompetencyLevel.INTERMEDIATE,
                        "weight": 0.4,
                        "position": 1,
                        "competency": competency,
                        "sub_competency": sub2,
                    }
                ),
            ],
        }
    )
    for node in vacancy.category_nodes:
        node.vacancy_id = vacancy.id
    for node in vacancy.competency_nodes:
        node.vacancy_id = vacancy.id
    for node in vacancy.sub_competency_nodes:
        node.vacancy_id = vacancy.id
    return vacancy, category, competency, sub1, sub2
