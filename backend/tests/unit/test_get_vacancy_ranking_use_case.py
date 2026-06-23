from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.ranking import GetVacancyRankingUseCase
from tests.factories import CandidateFactory
from tests.fixtures.domain_graph import build_vacancy_with_graph

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return GetVacancyRankingUseCase(mock_uow)


async def test_get_vacancy_ranking_use_case_always_recalculates(
    use_case: GetVacancyRankingUseCase, mock_uow
) -> None:
    vacancy, _, _, _, _ = build_vacancy_with_graph()
    candidate = CandidateFactory().make({"vacancy_id": vacancy.id})

    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.candidates.list_by_vacancy.return_value = [candidate]
    mock_uow.ranking_snapshots.get_by_vacancy.return_value = None

    result = await use_case.execute(vacancy.id)

    assert result.vacancy_id == vacancy.id
    mock_uow.candidates.list_by_vacancy.assert_awaited_once()
    mock_uow.ranking_snapshots.add.assert_awaited_once()


async def test_get_vacancy_ranking_use_case_raises_when_vacancy_not_found(
    use_case: GetVacancyRankingUseCase, mock_uow
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4())
