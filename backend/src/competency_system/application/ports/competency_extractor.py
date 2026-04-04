from __future__ import annotations

from typing import Protocol

from competency_system.domain.entities.competency import (
    Category,
    Competency,
    SubCompetency,
)


class LLMCompetencyExtractor(Protocol):
    async def extract_categories(
        self,
        vacancy_name: str,
        vacancy_description: str,
        existing_categories: list[Category],
    ) -> list[Category]: ...

    async def extract_competencies(
        self,
        vacancy_name: str,
        vacancy_description: str,
        category: Category,
    ) -> list[Competency]: ...

    async def extract_subcompetencies(
        self,
        vacancy_name: str,
        vacancy_description: str,
        competency: Competency,
    ) -> list[SubCompetency]: ...
