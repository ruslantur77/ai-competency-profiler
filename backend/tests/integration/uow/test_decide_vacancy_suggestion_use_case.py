from __future__ import annotations

from typing import Any

import pytest

from competency_system.application.dtos.vacancy import VacancySuggestionDecisionDTO
from competency_system.application.ports.repositories import VacancyInclude
from competency_system.application.use_cases.vacancy import (
    DecideVacancySuggestionUseCase,
)
from competency_system.domain.entities import Vacancy
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
)
from tests.factories import VacancyGraphSuggestionFactory

pytestmark = pytest.mark.integration_repo


async def test_decide_approved_category_creates_ontology_node_and_vacancy_mapping(
    uow_factory: Any,
) -> None:
    vacancy = Vacancy(name="Backend", description="Build APIs")
    suggestion = VacancyGraphSuggestionFactory().make(
        {
            "vacancy_id": vacancy.id,
            "stage": SuggestionStage.CATEGORY,
            "entity_type": SuggestionEntityType.CATEGORY,
            "status": SuggestionStatus.PENDING,
            "name": "Data",
            "description": "Data competencies",
        }
    )

    async with uow_factory() as uow:
        await uow.vacancies.add(vacancy)
        await uow.vacancy_suggestions.add(suggestion)
        await uow.commit()

    use_case = DecideVacancySuggestionUseCase(uow_factory())
    result = await use_case.execute(
        vacancy.id,
        VacancySuggestionDecisionDTO(
            suggestion_id=suggestion.id,
            status=SuggestionStatus.APPROVED,
        ),
    )

    assert result.status == SuggestionStatus.APPROVED

    async with uow_factory() as uow:
        saved_suggestion = await uow.vacancy_suggestions.get(suggestion.id)
        loaded_vacancy = await uow.vacancies.get(
            vacancy.id, include={VacancyInclude.NORMALIZED_GRAPH}
        )
        assert saved_suggestion is not None
        assert saved_suggestion.status == SuggestionStatus.APPROVED
        assert loaded_vacancy is not None
        assert len(loaded_vacancy.category_nodes) == 1
        assert loaded_vacancy.competency_nodes == []
        assert loaded_vacancy.sub_competency_nodes == []

        created_category_id = loaded_vacancy.category_nodes[0].category_id
        created_category = await uow.categories.get(created_category_id)
        assert created_category is not None
        assert created_category.name == "Data"
        assert created_category.description == "Data competencies"
