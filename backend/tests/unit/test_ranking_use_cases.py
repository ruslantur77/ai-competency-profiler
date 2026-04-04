from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from competency_system.application.dtos.webhooks import (
    RankingSnapshot,
    RankingSnapshotPayload,
)
from competency_system.application.use_cases.ranking import GetVacancyRankingUseCase
from competency_system.domain.entities import Vacancy

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_get_vacancy_ranking_uses_existing_snapshot(mock_uow) -> None:
    vacancy_id = uuid4()
    mock_uow.vacancies.get.return_value = Vacancy(
        id=vacancy_id,
        name="Backend",
        description="Role",
    )
    snapshot = RankingSnapshot(
        id=uuid4(),
        vacancy_id=vacancy_id,
        payload=RankingSnapshotPayload(
            data={"vacancy_id": str(vacancy_id), "rankings": []}
        ),
        calculated_at=datetime.now(UTC),
    )
    mock_uow.ranking_snapshots.get_by_vacancy.return_value = snapshot

    result = await GetVacancyRankingUseCase(mock_uow).execute(vacancy_id)

    assert result.vacancy_id == vacancy_id
    assert result.rankings == []
