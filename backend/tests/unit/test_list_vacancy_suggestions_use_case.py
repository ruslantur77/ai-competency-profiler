from __future__ import annotations

import pytest

from competency_system.application.use_cases.vacancy import (
    ListVacancySuggestionsUseCase,
)
from tests.factories import VacancyFactory, VacancyGraphSuggestionFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return ListVacancySuggestionsUseCase(mock_uow)


async def test_list_vacancy_suggestions_use_case_returns_mapped_list(
    use_case: ListVacancySuggestionsUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    suggestions = [
        VacancyGraphSuggestionFactory().make({"vacancy_id": vacancy.id, "name": "SQL"}),
        VacancyGraphSuggestionFactory().make(
            {"vacancy_id": vacancy.id, "name": "Caching"}
        ),
    ]
    mock_uow.vacancy_suggestions.list_by_vacancy.return_value = suggestions

    result = await use_case.execute(vacancy.id)

    assert [item.name for item in result] == ["SQL", "Caching"]
    mock_uow.vacancy_suggestions.list_by_vacancy.assert_awaited_once_with(vacancy.id)


async def test_list_vacancy_suggestions_use_case_returns_empty_list(
    use_case: ListVacancySuggestionsUseCase, mock_uow
) -> None:
    mock_uow.vacancy_suggestions.list_by_vacancy.return_value = []

    result = await use_case.execute(VacancyFactory().make().id)

    assert result == []
