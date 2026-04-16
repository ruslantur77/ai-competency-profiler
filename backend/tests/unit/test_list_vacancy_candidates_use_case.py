from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.candidate import (
    ListVacancyCandidatesUseCase,
)
from tests.factories import CandidateFactory, VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return ListVacancyCandidatesUseCase(mock_uow)


async def test_list_vacancy_candidates_use_case_returns_items(
    use_case: ListVacancyCandidatesUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    candidate = CandidateFactory().make({"vacancy_id": vacancy.id})
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.candidates.list_by_vacancy.return_value = [candidate]

    result = await use_case.execute(vacancy.id)

    assert len(result) == 1
    assert result[0].id == candidate.id
    assert result[0].external_id == candidate.external_id
    assert result[0].vacancy_id == vacancy.id
    mock_uow.candidates.list_by_vacancy.assert_awaited_once_with(vacancy.id)


async def test_list_vacancy_candidates_use_case_raises_when_vacancy_not_found(
    use_case: ListVacancyCandidatesUseCase, mock_uow
) -> None:
    vacancy_id = uuid4()
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(vacancy_id)
