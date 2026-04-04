from __future__ import annotations

import pytest

from competency_system.application.use_cases.vacancy import (
    ListVacanciesForReviewUseCase,
)
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return ListVacanciesForReviewUseCase(mock_uow)


async def test_list_vacancies_for_review_use_case_returns_expected_statuses(
    use_case: ListVacanciesForReviewUseCase, mock_uow
) -> None:
    rows = [
        VacancyFactory().make({"status": VacancyStatus.DRAFT}),
        VacancyFactory().make({"status": VacancyStatus.PENDING}),
        VacancyFactory().make({"status": VacancyStatus.FAILED}),
    ]
    mock_uow.vacancies.list_by_statuses.return_value = rows

    result = await use_case.execute()

    assert len(result) == 3
    called_statuses = mock_uow.vacancies.list_by_statuses.await_args.args[0]
    assert called_statuses == {
        VacancyStatus.DRAFT,
        VacancyStatus.PENDING,
        VacancyStatus.FAILED,
    }


async def test_list_vacancies_for_review_use_case_returns_empty_list(
    use_case: ListVacanciesForReviewUseCase, mock_uow
) -> None:
    mock_uow.vacancies.list_by_statuses.return_value = []

    result = await use_case.execute()

    assert result == []
