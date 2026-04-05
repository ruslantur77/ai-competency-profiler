from __future__ import annotations

import pytest

from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
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
