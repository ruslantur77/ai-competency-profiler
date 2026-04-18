from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.candidate import (
    DeleteCandidateUseCase,
    GetCandidateUseCase,
    ListCandidatesUseCase,
)
from tests.factories.domain import CandidateFactory

pytestmark = pytest.mark.unit


async def test_list_candidates_use_case_returns_items(mock_uow) -> None:
    use_case = ListCandidatesUseCase(mock_uow)
    candidate = CandidateFactory().make()
    mock_uow.candidates.get_list.return_value = [candidate]
    mock_uow.candidates.count.return_value = 1

    result = await use_case.execute(limit=50, offset=0)

    assert len(result.items) == 1
    assert result.items[0].id == candidate.id
    assert result.total == 1
    assert result.limit == 50
    assert result.offset == 0
    mock_uow.candidates.get_list.assert_awaited_once_with(limit=50, offset=0)
    mock_uow.candidates.count.assert_awaited_once()


async def test_get_candidate_use_case_raises_when_missing(mock_uow) -> None:
    use_case = GetCandidateUseCase(mock_uow)
    candidate_id = uuid4()
    mock_uow.candidates.get.return_value = None

    with pytest.raises(NotFoundError):
        await use_case.execute(candidate_id)


async def test_delete_candidate_use_case_soft_deletes(mock_uow) -> None:
    use_case = DeleteCandidateUseCase(mock_uow)
    candidate = CandidateFactory().make()
    mock_uow.candidates.soft_delete.return_value = candidate

    await use_case.execute(candidate.id)

    mock_uow.candidates.soft_delete.assert_awaited_once_with(candidate.id)
    mock_uow.commit.assert_awaited_once()
