from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    SubCompetency,
    Vacancy,
)
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.infrastructure.persistence.models import CategoryOrm, VacancyOrm
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork

pytestmark = pytest.mark.integration_repo


def _build_category() -> Category:
    sub = SubCompetency(name="REST", weight=1.0)
    competency = Competency(
        category_id=uuid4(),
        name="Backend",
        sub_competencies=[sub],
    )
    category = Category(name="Engineering", competencies=[competency])
    competency.category_id = category.id
    return category


@pytest.mark.asyncio
async def test_uow_initializes_all_repositories(
    pg_session_factory: async_sessionmaker,
) -> None:
    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        assert uow.categories is not None
        assert uow.competencies is not None
        assert uow.sub_competencies is not None
        assert uow.vacancies is not None
        assert uow.candidates is not None
        assert uow.tasks is not None
        assert uow.test_results is not None
        assert uow.vacancy_suggestions is not None
        assert uow.webhook_events is not None
        assert uow.ranking_snapshots is not None
        assert uow.users is not None
        assert uow.refresh_tokens is not None


@pytest.mark.asyncio
async def test_uow_commit_persists_data(pg_session_factory: async_sessionmaker) -> None:
    vacancy = Vacancy(
        name="Backend Engineer",
        description="Build APIs",
        status=VacancyStatus.DRAFT,
    )

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        await uow.vacancies.add(vacancy)
        await uow.commit()

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        loaded = await uow.vacancies.get(vacancy.id)

    assert loaded is not None
    assert loaded.name == vacancy.name


@pytest.mark.asyncio
async def test_uow_rolls_back_on_exception(
    pg_session_factory: async_sessionmaker,
) -> None:
    vacancy = Vacancy(name="Temp", description="Should rollback")

    with pytest.raises(RuntimeError):
        async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
            await uow.vacancies.add(vacancy)
            raise RuntimeError("boom")

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        assert await uow.vacancies.get(vacancy.id) is None


@pytest.mark.asyncio
async def test_uow_flush_makes_pending_data_queryable_within_transaction(
    pg_session_factory: async_sessionmaker,
) -> None:
    vacancy_id = uuid4()

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        uow.session.add(
            VacancyOrm(
                id=vacancy_id,
                name="Flush vacancy",
                description="Created via session",
                status=VacancyStatus.DRAFT,
            )
        )
        await uow.flush()
        loaded = await uow.vacancies.get(vacancy_id)
        assert loaded is not None
        await uow.rollback()

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        assert await uow.vacancies.get(vacancy_id) is None


@pytest.mark.asyncio
async def test_uow_atomicity_across_multiple_repositories(
    pg_session_factory: async_sessionmaker,
) -> None:
    category = _build_category()
    vacancy = Vacancy(
        name="Backend",
        description="Role",
        status=VacancyStatus.READY,
        categories=[category],
        competencies=category.competencies,
    )
    candidate = Candidate(external_id="cand-uow", vacancy_id=vacancy.id)

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        await uow.categories.add(category)
        await uow.vacancies.add(vacancy)
        await uow.candidates.add(candidate)
        await uow.commit()

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        loaded_vacancy = await uow.vacancies.get(vacancy.id)
        loaded_candidate = await uow.candidates.get_by_external_id("cand-uow")

    assert loaded_vacancy is not None
    assert loaded_candidate is not None


@pytest.mark.asyncio
async def test_uow_rollback_keeps_state_consistent_for_multiple_repositories(
    pg_session_factory: async_sessionmaker,
) -> None:
    category = _build_category()
    vacancy = Vacancy(
        name="Backend",
        description="Role",
        status=VacancyStatus.READY,
        categories=[category],
        competencies=category.competencies,
    )

    with pytest.raises(RuntimeError):
        async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
            await uow.categories.add(category)
            await uow.vacancies.add(vacancy)
            raise RuntimeError("force rollback")

    async with SQLAlchemyUnitOfWork(pg_session_factory) as uow:
        assert await uow.vacancies.get(vacancy.id) is None
        category_count = await uow.session.scalar(select(CategoryOrm.id).limit(1))
        assert category_count is None
