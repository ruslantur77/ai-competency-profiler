from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.use_cases.candidate import GetCandidateProfileUseCase
from tests.factories import CandidateAchievementFactory, CandidateFactory
from tests.fixtures.domain_graph import build_vacancy_with_graph

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return GetCandidateProfileUseCase(mock_uow)


async def test_get_candidate_profile_use_case_returns_profile(
    use_case: GetCandidateProfileUseCase, mock_uow
) -> None:
    vacancy, _, _, sub1, _ = build_vacancy_with_graph()
    candidate = CandidateFactory().make({"vacancy_id": vacancy.id})
    candidate.achievements = [
        CandidateAchievementFactory().make(
            {"candidate_id": candidate.id, "sub_competency_id": sub1.id}
        )
    ]
    mock_uow.candidates.get.return_value = candidate
    mock_uow.vacancies.get.return_value = vacancy

    result = await use_case.execute(candidate.id)

    assert result.candidate_id == candidate.id
    assert result.total_score >= 0.0
    mock_uow.candidates.get.assert_awaited_once()
    mock_uow.vacancies.get.assert_awaited_once()


async def test_get_candidate_profile_use_case_raises_when_candidate_not_found(
    use_case: GetCandidateProfileUseCase, mock_uow
) -> None:
    mock_uow.candidates.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4())


async def test_get_candidate_profile_use_case_raises_when_vacancy_not_found(
    use_case: GetCandidateProfileUseCase, mock_uow
) -> None:
    candidate = CandidateFactory().make()
    mock_uow.candidates.get.return_value = candidate
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(ValueError, match="Vacancy"):
        await use_case.execute(candidate.id)
