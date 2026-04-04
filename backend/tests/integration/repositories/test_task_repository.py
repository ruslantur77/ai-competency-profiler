from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import TaskInclude
from competency_system.domain.entities import (
    Task,
    TaskSubCompetencyMapping,
)
from competency_system.domain.value_objects.enums import TaskType
from competency_system.infrastructure.persistence.repositories import (
    CategoryRepository,
    TaskRepository,
)
from tests.fixtures.domain_graph import build_taxonomy

pytestmark = pytest.mark.integration_repo


async def test_task_repository_special_methods_and_mapping_replace(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    repo = TaskRepository(pg_session)

    category, _, sub1, sub2 = build_taxonomy()
    await category_repo.add(category)

    task = Task(
        external_id="task-1",
        title="API Task",
        type=TaskType.CODE,
        sub_competency_mappings=[
            TaskSubCompetencyMapping(sub_competency_id=sub1.id, weight=1.0)
        ],
    )
    await repo.add(task)
    await pg_session.commit()

    loaded = await repo.get(task.id, include={TaskInclude.SUB_COMPETENCY_MAPPINGS})
    assert loaded is not None
    assert [m.sub_competency_id for m in loaded.sub_competency_mappings] == [sub1.id]

    by_external = await repo.get_by_external_id(
        "task-1",
        include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
    )
    assert by_external is not None

    task.sub_competency_mappings = [
        TaskSubCompetencyMapping(sub_competency_id=sub2.id, weight=0.4),
        TaskSubCompetencyMapping(sub_competency_id=sub1.id, weight=0.6),
    ]
    await repo.add(task)
    await pg_session.commit()

    updated = await repo.get(task.id, include={TaskInclude.SUB_COMPETENCY_MAPPINGS})
    assert updated is not None
    assert [m.sub_competency_id for m in updated.sub_competency_mappings] == [
        sub2.id,
        sub1.id,
    ]
