from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.dtos.webhooks import WebhookEvent, WebhookEventStatus
from competency_system.domain.entities import Vacancy
from competency_system.infrastructure.persistence.models import WebhookEventOrm
from competency_system.infrastructure.persistence.repositories import (
    VacancyRepository,
    WebhookEventRepository,
)

pytestmark = pytest.mark.integration_repo


async def test_webhook_event_repository_special_method_and_uniqueness(
    pg_session: AsyncSession,
) -> None:
    vacancy_repo = VacancyRepository(pg_session)
    repo = WebhookEventRepository(pg_session)

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    event = WebhookEvent(
        event_id="evt-1",
        vacancy_id=vacancy.id,
        candidate_external_id="cand-1",
        task_external_id="task-1",
        status=WebhookEventStatus.PROCESSED,
        payload={"passed": 5, "total": 5},
    )
    await repo.add(event)
    await pg_session.commit()

    loaded = await repo.get_by_event_id("evt-1")
    assert loaded is not None
    assert loaded.payload.data == {"passed": 5, "total": 5}

    with pytest.raises(IntegrityError):
        await repo.add(
            WebhookEvent(
                event_id="evt-1",
                vacancy_id=vacancy.id,
                candidate_external_id="cand-2",
                task_external_id="task-2",
            )
        )


async def test_webhook_event_repository_base_list_delete(
    pg_session: AsyncSession,
) -> None:
    vacancy_repo = VacancyRepository(pg_session)
    repo = WebhookEventRepository(pg_session)

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    event = WebhookEvent(
        event_id=f"evt-{uuid4()}",
        vacancy_id=vacancy.id,
        candidate_external_id="candidate",
        task_external_id="task",
    )
    await repo.add(event)
    await pg_session.commit()

    listed = await repo.get_list()
    assert len(listed) == 1

    await repo.delete(event.id)
    await pg_session.commit()

    assert (
        await pg_session.scalar(select(func.count()).select_from(WebhookEventOrm)) == 0
    )
