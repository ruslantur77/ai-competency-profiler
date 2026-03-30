from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import VacancyInclude
from competency_system.domain.entities import SubCompetency
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.infrastructure.persistence.models import (
    VacancyCategoryNodeOrm,
    VacancyCompetencyNodeOrm,
    VacancySubCompetencyNodeOrm,
)
from competency_system.infrastructure.persistence.repositories import VacancyRepository

from .helpers import build_vacancy_with_graph

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_vacancy_repository_status_filter_and_normalized_graph(
    pg_session: AsyncSession,
) -> None:
    repo = VacancyRepository(pg_session)

    vacancy_a, category_a, competency_a, sub_a1, sub_a2 = build_vacancy_with_graph()
    vacancy_b, _, _, _, _ = build_vacancy_with_graph()
    vacancy_b.name = "Data Engineer"
    vacancy_b.status = VacancyStatus.DRAFT

    await repo.add(vacancy_a)
    await pg_session.commit()
    await asyncio.sleep(0.01)

    await repo.add(vacancy_b)
    await pg_session.commit()

    filtered = await repo.list_by_statuses({VacancyStatus.READY.value})
    assert len(filtered) == 1
    assert filtered[0].id == vacancy_a.id

    loaded = await repo.get(vacancy_a.id, include={VacancyInclude.NORMALIZED_GRAPH})
    assert loaded is not None
    assert len(loaded.categories) == 1
    assert loaded.categories[0].id == category_a.id
    assert len(loaded.competencies) == 1
    assert loaded.competencies[0].id == competency_a.id
    assert {sub.id for sub in loaded.competencies[0].sub_competencies} == {
        sub_a1.id,
        sub_a2.id,
    }


@pytest.mark.asyncio
async def test_vacancy_repository_replaces_normalized_nodes_on_update(
    pg_session: AsyncSession,
) -> None:
    repo = VacancyRepository(pg_session)
    vacancy, _, competency, sub1, sub2 = build_vacancy_with_graph()

    await repo.add(vacancy)
    await pg_session.commit()

    competency.sub_competencies = [
        SubCompetency(
            id=sub2.id,
            name=sub2.name,
            description=sub2.description,
            target_level=CompetencyLevel.EXPERT,
            weight=1.0,
        )
    ]
    vacancy.competencies = [competency]
    vacancy.categories = []

    await repo.add(vacancy)
    await pg_session.commit()

    loaded = await repo.get(vacancy.id, include={VacancyInclude.NORMALIZED_GRAPH})
    assert loaded is not None
    assert [sub.id for sub in loaded.competencies[0].sub_competencies] == [sub2.id]
    assert sub1.id not in {sub.id for sub in loaded.competencies[0].sub_competencies}

    category_nodes = await pg_session.scalar(
        select(func.count()).select_from(VacancyCategoryNodeOrm)
    )
    competency_nodes = await pg_session.scalar(
        select(func.count()).select_from(VacancyCompetencyNodeOrm)
    )
    sub_nodes = await pg_session.scalar(
        select(func.count()).select_from(VacancySubCompetencyNodeOrm)
    )
    assert category_nodes == 1
    assert competency_nodes == 1
    assert sub_nodes == 1
