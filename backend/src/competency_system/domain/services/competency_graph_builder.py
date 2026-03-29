from __future__ import annotations

from competency_system.domain.entities.competency import Category, Competency
from competency_system.domain.entities.vacancy import Vacancy


class CompetencyGraphBuilder:
    """Сервис для построения графа компетенций из вакансии.

    3-ступенчатый LLM пайплайн.
    """

    def __init__(
        self,
        llm_extractor,  # Просто передаем объект, без Protocol
        max_categories: int = 6,
        max_competencies: int = 10,
        max_subcompetencies: int = 6,
    ):
        self.llm_extractor = llm_extractor
        self.max_categories = max_categories
        self.max_competencies = max_competencies
        self.max_subcompetencies = max_subcompetencies

    async def build_graph(
        self,
        vacancy: Vacancy,
        existing_categories: list[Category],
    ) -> tuple[list[Category], list[Competency]]:
        """Построить граф компетенций для вакансии.

        Returns:
            (categories, competencies) - готовый граф
        """
        # Шаг 1: Извлечь категории
        categories = await self.llm_extractor.extract_categories(
            vacancy.name,
            vacancy.description,
            existing_categories,
        )
        categories = categories[: self.max_categories]

        # Шаг 2: Извлечь компетенции для каждой категории
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

        # Шаг 3: Извлечь подкомпетенции
        for competency in all_competencies:
            subcompetencies = await self.llm_extractor.extract_subcompetencies(
                vacancy.name,
                vacancy.description,
                competency,
            )
            subcompetencies = subcompetencies[: self.max_subcompetencies]

            # Распределить веса равномерно
            if subcompetencies:
                weight = 1.0 / len(subcompetencies)
                for sub in subcompetencies:
                    sub.weight = weight

            competency.sub_competencies = subcompetencies

        return categories, all_competencies
