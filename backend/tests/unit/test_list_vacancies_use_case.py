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
    mock_uow.vacancies.count_by_statuses.return_value = 2

    result = await use_case.execute(statuses=statuses, limit=10, offset=0)

    assert [item.name for item in result.items] == ["Draft vacancy", "Failed vacancy"]
    assert result.total == 2
    mock_uow.vacancies.list_by_statuses.assert_awaited_once_with(
        statuses, limit=10, offset=0
    )
    mock_uow.vacancies.count_by_statuses.assert_awaited_once_with(statuses)


async def test_list_vacancies_use_case_returns_empty_list(
    use_case: ListVacanciesUseCase, mock_uow
) -> None:
    mock_uow.vacancies.list_by_statuses.return_value = []
    mock_uow.vacancies.count_by_statuses.return_value = 0

    result = await use_case.execute(statuses={VacancyStatus.READY}, limit=10, offset=0)

    assert result.items == []
    assert result.total == 0


async def test_list_vacancies_use_case_without_filter_returns_all(
    use_case: ListVacanciesUseCase, mock_uow
) -> None:
    rows = [
        VacancyFactory().make({"status": VacancyStatus.DRAFT}),
        VacancyFactory().make({"status": VacancyStatus.READY}),
    ]
    mock_uow.vacancies.list_by_statuses.return_value = rows
    mock_uow.vacancies.count_by_statuses.return_value = 2

    result = await use_case.execute(limit=20, offset=0)

    assert len(result.items) == 2
    assert result.total == 2
    mock_uow.vacancies.list_by_statuses.assert_awaited_once_with(
        None, limit=20, offset=0
    )
