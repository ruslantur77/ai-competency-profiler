from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.domain.entities import Vacancy, VacancyGraphSuggestion
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
)
from competency_system.infrastructure.persistence.repositories import (
    VacancyRepository,
    VacancySuggestionRepository,
)

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_vacancy_suggestion_repository_list_by_vacancy(
    pg_session: AsyncSession,
) -> None:
    vacancy_repo = VacancyRepository(pg_session)
    repo = VacancySuggestionRepository(pg_session)

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    first = VacancyGraphSuggestion(
        vacancy_id=vacancy.id,
        stage=SuggestionStage.CATEGORY,
        entity_type=SuggestionEntityType.CATEGORY,
        status=SuggestionStatus.PENDING,
        name="Data",
    )
    second = VacancyGraphSuggestion(
        vacancy_id=vacancy.id,
        stage=SuggestionStage.COMPETENCY,
        entity_type=SuggestionEntityType.COMPETENCY,
        status=SuggestionStatus.APPROVED,
        name="Caching",
    )

    await repo.add(first)
    await pg_session.commit()
    await asyncio.sleep(0.01)

    await repo.add(second)
    await pg_session.commit()

    listed = await repo.list_by_vacancy(vacancy.id)
    assert [item.id for item in listed] == [first.id, second.id]

    with pytest.raises(IntegrityError):
        await repo.add(
            VacancyGraphSuggestion(
                vacancy_id=uuid4(),
                stage=SuggestionStage.CATEGORY,
                entity_type=SuggestionEntityType.CATEGORY,
                name="Invalid",
            )
        )
