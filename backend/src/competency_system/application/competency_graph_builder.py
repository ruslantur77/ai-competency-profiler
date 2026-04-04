from __future__ import annotations

from competency_system.application.ports.competency_extractor import (
    LLMCompetencyExtractor,
)
from competency_system.domain.entities.competency import (
    Category,
    Competency,
)
from competency_system.domain.entities.vacancy import Vacancy


class CompetencyGraphBuilder:
    def __init__(
        self,
        llm_extractor: LLMCompetencyExtractor,
        max_categories: int = 6,
        max_competencies: int = 10,
        max_subcompetencies: int = 6,
    ) -> None:
        self.llm_extractor = llm_extractor
        self.max_categories = max_categories
        self.max_competencies = max_competencies
        self.max_subcompetencies = max_subcompetencies

    async def build_graph(
        self,
        vacancy: Vacancy,
        existing_categories: list[Category],
    ) -> tuple[list[Category], list[Competency]]:
        # Step 1: Extract categories from vacancy description
        categories = await self.llm_extractor.extract_categories(
            vacancy.name,
            vacancy.description,
            existing_categories,
        )
        categories = categories[: self.max_categories]

        # Step 2: Extract competencies for each category
        all_competencies: list[Competency] = []
        for category in categories:
            competencies = await self.llm_extractor.extract_competencies(
                vacancy.name,
                vacancy.description,
                category,
            )
            competencies = competencies[: self.max_competencies]

            for comp in competencies:
                comp.category_id = category.id

            all_competencies.extend(competencies)

        # Step 3: Extract sub-competencies for each competency
        for competency in all_competencies:
            subcompetencies = await self.llm_extractor.extract_subcompetencies(
                vacancy.name,
                vacancy.description,
                competency,
            )
            competency.sub_competencies = subcompetencies[: self.max_subcompetencies]

        return categories, all_competencies
