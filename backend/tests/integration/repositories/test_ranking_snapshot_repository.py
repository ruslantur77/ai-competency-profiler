from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.dtos.webhooks import RankingSnapshot
from competency_system.domain.entities import Vacancy
from competency_system.infrastructure.persistence.models import RankingSnapshotOrm
from competency_system.infrastructure.persistence.repositories import (
    RankingSnapshotRepository,
    VacancyRepository,
)

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_ranking_snapshot_repository_get_by_vacancy_and_upsert(
    pg_session: AsyncSession,
) -> None:
    vacancy_repo = VacancyRepository(pg_session)
    repo = RankingSnapshotRepository(pg_session)

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    snapshot = RankingSnapshot(
        id=uuid4(),
        vacancy_id=vacancy.id,
        payload={"rankings": [{"candidate": "cand-1"}]},
        calculated_at=datetime.now(UTC),
    )
    await repo.add(snapshot)
    await pg_session.commit()

    loaded = await repo.get_by_vacancy(vacancy.id)
    assert loaded is not None
    assert loaded.payload.data["rankings"][0]["candidate"] == "cand-1"

    snapshot.payload.data = {"rankings": [{"candidate": "cand-2"}]}
    await repo.add(snapshot)
    await pg_session.commit()

    updated = await repo.get_by_vacancy(vacancy.id)
    assert updated is not None
    assert updated.payload.data["rankings"][0]["candidate"] == "cand-2"

    row_count = await pg_session.scalar(
        select(func.count()).select_from(RankingSnapshotOrm)
    )
    assert row_count == 1

    with pytest.raises(IntegrityError):
        await repo.add(
            RankingSnapshot(
                id=uuid4(),
                vacancy_id=vacancy.id,
                payload={"rankings": []},
                calculated_at=datetime.now(UTC),
            )
        )
