from __future__ import annotations

import pytest

from competency_system.application.competency_graph_builder import (
    CompetencyGraphBuilder,
)
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
)

pytestmark = pytest.mark.unit


class _Extractor:
    def __init__(self) -> None:
        self.category_calls = 0
        self.competency_calls = 0
        self.sub_calls = 0

    async def extract_categories(
        self, vacancy_name, vacancy_description, existing_categories
    ):  # type: ignore[no-untyped-def]
        self.category_calls += 1
        return [
            Category(name="Backend"),
            Category(name="Frontend"),
            Category(name="Data"),
        ]

    async def extract_competencies(self, vacancy_name, vacancy_description, category):  # type: ignore[no-untyped-def]
        self.competency_calls += 1
        return [
            Competency(category_id=category.id, name=f"{category.name}-A"),
            Competency(category_id=category.id, name=f"{category.name}-B"),
        ]

    async def extract_subcompetencies(
        self, vacancy_name, vacancy_description, competency
    ):  # type: ignore[no-untyped-def]
        self.sub_calls += 1
        return [
            SubCompetency(competency_id=competency.id, name="S1"),
            SubCompetency(competency_id=competency.id, name="S2"),
        ]


async def test_competency_graph_builder_applies_limits_and_sets_relations() -> None:
    extractor = _Extractor()
    builder = CompetencyGraphBuilder(
        extractor,
        max_categories=2,
        max_competencies=1,
        max_subcompetencies=1,
    )
    vacancy = Vacancy(name="Python Engineer", description="Build systems")

    categories, competencies = await builder.build_graph(vacancy, [])

    assert len(categories) == 2
    assert len(competencies) == 2
    assert all(len(comp.sub_competencies) == 1 for comp in competencies)
    assert all(
        comp.category_id in {cat.id for cat in categories} for comp in competencies
    )
    assert extractor.category_calls == 1
    assert extractor.competency_calls == 2
    assert extractor.sub_calls == 2
