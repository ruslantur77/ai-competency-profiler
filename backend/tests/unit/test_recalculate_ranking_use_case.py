from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from competency_system.application.dtos.webhooks import (
    RankingSnapshot,
    RankingSnapshotPayload,
)
from competency_system.application.use_cases.ranking import RecalculateRankingUseCase
from tests.factories import CandidateFactory
from tests.fixtures.domain_graph import build_vacancy_with_graph

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return RecalculateRankingUseCase(mock_uow)


async def test_recalculate_ranking_use_case_creates_snapshot(
    use_case: RecalculateRankingUseCase, mock_uow
) -> None:
    vacancy, _, _, _, _ = build_vacancy_with_graph()
    candidate = CandidateFactory().make({"vacancy_id": vacancy.id})
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.candidates.list_by_vacancy.return_value = [candidate]
    mock_uow.ranking_snapshots.get_by_vacancy.return_value = None

    result = await use_case.execute(vacancy.id)

    assert result.vacancy_id == vacancy.id
    mock_uow.ranking_snapshots.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


async def test_recalculate_ranking_use_case_raises_when_vacancy_not_found(
    use_case: RecalculateRankingUseCase, mock_uow
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4())


async def test_recalculate_ranking_use_case_updates_existing_snapshot(
    use_case: RecalculateRankingUseCase, mock_uow
) -> None:
    vacancy, _, _, _, _ = build_vacancy_with_graph()
    candidate = CandidateFactory().make({"vacancy_id": vacancy.id})
    existing = RankingSnapshot(
        id=uuid4(),
        vacancy_id=vacancy.id,
        payload=RankingSnapshotPayload(
            data={"vacancy_id": str(vacancy.id), "rankings": []}
        ),
        calculated_at=datetime.now(UTC),
    )
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.candidates.list_by_vacancy.return_value = [candidate]
    mock_uow.ranking_snapshots.get_by_vacancy.return_value = existing

    await use_case.execute(vacancy.id)

    mock_uow.ranking_snapshots.add.assert_awaited_once_with(existing)
    mock_uow.commit.assert_awaited_once()
