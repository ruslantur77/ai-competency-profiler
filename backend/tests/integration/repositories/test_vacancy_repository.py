from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import VacancyInclude
from competency_system.domain.entities import VacancySubCompetencyNode
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.infrastructure.persistence.models import (
    VacancyCategoryNodeOrm,
    VacancyCompetencyNodeOrm,
    VacancySubCompetencyNodeOrm,
)
from competency_system.infrastructure.persistence.repositories import (
    CategoryRepository,
    VacancyRepository,
)
from tests.fixtures.domain_graph import build_vacancy_with_graph

pytestmark = pytest.mark.integration_repo


async def test_vacancy_repository_status_filter_and_normalized_graph(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    repo = VacancyRepository(pg_session)

    vacancy_a, category_a, competency_a, sub_a1, sub_a2 = build_vacancy_with_graph()
    vacancy_b, category_b, _, _, _ = build_vacancy_with_graph()
    vacancy_b.name = "Data Engineer"
    vacancy_b.status = VacancyStatus.DRAFT

    await category_repo.add(category_a)
    await category_repo.add(category_b)
    await pg_session.commit()

    await repo.add(vacancy_a)
    await repo.add(vacancy_b)
    await pg_session.commit()

    filtered = await repo.list_by_statuses({VacancyStatus.READY})
    assert len(filtered) == 1
    assert filtered[0].id == vacancy_a.id

    loaded = await repo.get(vacancy_a.id, include={VacancyInclude.NORMALIZED_GRAPH})
    assert loaded is not None
    assert len(loaded.category_nodes) == 1
    assert loaded.category_nodes[0].category_id == category_a.id
    assert len(loaded.competency_nodes) == 1
    assert loaded.competency_nodes[0].competency_id == competency_a.id
    assert {node.sub_competency_id for node in loaded.sub_competency_nodes} == {
        sub_a1.id,
        sub_a2.id,
    }


async def test_vacancy_repository_replaces_normalized_nodes_on_update(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    repo = VacancyRepository(pg_session)
    vacancy, category, competency, sub1, sub2 = build_vacancy_with_graph()

    await category_repo.add(category)
    await pg_session.commit()

    await repo.add(vacancy)
    await pg_session.commit()

    vacancy.sub_competency_nodes = [
        VacancySubCompetencyNode(
            vacancy_id=vacancy.id,
            sub_competency_id=sub2.id,
            competency_id=competency.id,
            target_level=CompetencyLevel.EXPERT,
            weight=1.0,
            position=0,
        )
    ]
    await repo.add(vacancy)
    await pg_session.commit()

    loaded = await repo.get(vacancy.id, include={VacancyInclude.NORMALIZED_GRAPH})
    assert loaded is not None
    assert [node.sub_competency_id for node in loaded.sub_competency_nodes] == [sub2.id]
    assert sub1.id not in {
        node.sub_competency_id for node in loaded.sub_competency_nodes
    }

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


async def test_vacancy_repository_soft_delete_restore_and_hard_delete(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    repo = VacancyRepository(pg_session)
    vacancy, category, _, _, _ = build_vacancy_with_graph()

    await category_repo.add(category)
    await pg_session.commit()
    await repo.add(vacancy)
    await pg_session.commit()

    deleted = await repo.soft_delete(vacancy.id)
    await pg_session.commit()
    assert deleted is not None
    assert deleted.deleted_at is not None

    hidden = await repo.get(vacancy.id)
    assert hidden is None

    visible_with_deleted = await repo.get(vacancy.id, include_deleted=True)
    assert visible_with_deleted is not None
    assert visible_with_deleted.deleted_at is not None

    restored = await repo.restore(vacancy.id)
    await pg_session.commit()
    assert restored is not None
    assert restored.deleted_at is None
    assert await repo.get(vacancy.id) is not None

    await repo.hard_delete(vacancy.id)
    await pg_session.commit()
    assert await repo.get(vacancy.id, include_deleted=True) is None
