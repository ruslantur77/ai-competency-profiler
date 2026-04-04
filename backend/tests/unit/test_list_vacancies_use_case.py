from __future__ import annotations

import pytest

from competency_system.application.use_cases.vacancy import ListVacanciesUseCase
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return ListVacanciesUseCase(mock_uow)


async def test_list_vacancies_use_case_returns_filtered_rows(
    use_case: ListVacanciesUseCase, mock_uow
) -> None:
    rows = [
        VacancyFactory().make({"status": VacancyStatus.DRAFT, "name": "Draft vacancy"}),
        VacancyFactory().make(
            {"status": VacancyStatus.FAILED, "name": "Failed vacancy"}
        ),
    ]
    statuses = {VacancyStatus.DRAFT, VacancyStatus.FAILED}
    mock_uow.vacancies.list_by_statuses.return_value = rows

    result = await use_case.execute(statuses=statuses)

    assert [item.name for item in result] == ["Draft vacancy", "Failed vacancy"]
    mock_uow.vacancies.list_by_statuses.assert_awaited_once_with(statuses)


async def test_list_vacancies_use_case_returns_empty_list(
    use_case: ListVacanciesUseCase, mock_uow
) -> None:
    mock_uow.vacancies.list_by_statuses.return_value = []

    result = await use_case.execute(statuses={VacancyStatus.READY})

    assert result == []
