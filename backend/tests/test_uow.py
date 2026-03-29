from __future__ import annotations

import pytest

from competency_system.domain.entities import Vacancy
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


@pytest.mark.asyncio
async def test_uow_round_trip_vacancy(sqlite_session_factory) -> None:
    vacancy = Vacancy(
        name="Backend Engineer",
        description="Build backend services.",
        status=VacancyStatus.DRAFT,
        key_skills=["Python", "SQLAlchemy"],
    )

    async with SQLAlchemyUnitOfWork(sqlite_session_factory) as uow:
        await uow.vacancies.add(vacancy)
        await uow.commit()

    async with SQLAlchemyUnitOfWork(sqlite_session_factory) as uow:
        loaded = await uow.vacancies.get(vacancy.id)

    assert loaded is not None
    assert loaded.name == vacancy.name
    assert loaded.description == vacancy.description
    assert loaded.status == VacancyStatus.DRAFT
    assert loaded.key_skills == vacancy.key_skills
