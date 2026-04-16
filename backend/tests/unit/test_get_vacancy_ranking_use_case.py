from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from competency_system.application.dtos.webhooks import (
    RankingSnapshot,
    RankingSnapshotPayload,
)
from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.ranking import GetVacancyRankingUseCase
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return GetVacancyRankingUseCase(mock_uow)


async def test_get_vacancy_ranking_use_case_returns_cached_snapshot(
    use_case: GetVacancyRankingUseCase, mock_uow
) -> None:
    vacancy_id = uuid4()
    mock_uow.vacancies.get.return_value = VacancyFactory().make({"id": vacancy_id})
    mock_uow.ranking_snapshots.get_by_vacancy.return_value = RankingSnapshot(
        id=uuid4(),
        vacancy_id=vacancy_id,
        payload=RankingSnapshotPayload(
            data={"vacancy_id": str(vacancy_id), "rankings": []}
        ),
        calculated_at=datetime.now(UTC),
    )

    result = await use_case.execute(vacancy_id)

    assert result.vacancy_id == vacancy_id
    assert result.rankings == []


async def test_get_vacancy_ranking_use_case_raises_when_vacancy_not_found(
    use_case: GetVacancyRankingUseCase, mock_uow
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4())
