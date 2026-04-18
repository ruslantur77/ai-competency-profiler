from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import TaskInclude
from competency_system.domain.entities import (
    Task,
    TaskCategoryNode,
    TaskCompetencyNode,
    TaskSubCompetencyNode,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import TaskType
from competency_system.infrastructure.persistence.repositories import (
    CategoryRepository,
    TaskRepository,
)
from tests.fixtures.domain_graph import build_taxonomy

pytestmark = pytest.mark.integration_repo


async def test_task_repository_special_methods_and_graph_replace(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    repo = TaskRepository(pg_session)

    category, competency, sub1, sub2 = build_taxonomy()
    await category_repo.add(category)

    task = Task(
        external_id="task-1",
        title="API Task",
        type=TaskType.CODE,
        category_nodes=[
            TaskCategoryNode(category_id=category.id, position=0),
        ],
        competency_nodes=[
            TaskCompetencyNode(
                competency_id=competency.id,
                category_id=category.id,
                is_required=True,
                position=0,
            )
        ],
        sub_competency_nodes=[
            TaskSubCompetencyNode(
                sub_competency_id=sub1.id,
                competency_id=competency.id,
                target_level=CompetencyLevel.INTERMEDIATE,
                weight=1.0,
                position=0,
            )
        ],
    )
    await repo.add(task)
    await pg_session.commit()

    loaded = await repo.get(task.id, include={TaskInclude.NORMALIZED_GRAPH})
    assert loaded is not None
    assert [n.sub_competency_id for n in loaded.sub_competency_nodes] == [sub1.id]

    by_external = await repo.get_by_external_id(
        "task-1",
        include={TaskInclude.NORMALIZED_GRAPH},
    )
    assert by_external is not None

    task.sub_competency_nodes = [
        TaskSubCompetencyNode(
            sub_competency_id=sub2.id,
            competency_id=competency.id,
            target_level=CompetencyLevel.INTERMEDIATE,
            weight=0.4,
            position=0,
        ),
        TaskSubCompetencyNode(
            sub_competency_id=sub1.id,
            competency_id=competency.id,
            target_level=CompetencyLevel.ADVANCED,
            weight=0.6,
            position=1,
        ),
    ]
    await repo.add(task)
    await pg_session.commit()

    updated = await repo.get(task.id, include={TaskInclude.NORMALIZED_GRAPH})
    assert updated is not None
    assert [n.sub_competency_id for n in updated.sub_competency_nodes] == [
        sub2.id,
        sub1.id,
    ]
