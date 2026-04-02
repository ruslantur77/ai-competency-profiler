from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import TaskInclude
from competency_system.domain.entities import (
    Task,
    TaskSubCompetencyMapping,
    Vacancy,
    WebhookEvent,
)
from competency_system.domain.value_objects.enums import TaskType
from competency_system.infrastructure.persistence.models import TaskOrm, WebhookEventOrm
from competency_system.infrastructure.persistence.repositories import (
    CategoryRepository,
    TaskRepository,
    VacancyRepository,
    WebhookEventRepository,
)

from .helpers import build_taxonomy

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
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
        include={TaskInclude.SUB_COMPETENCY_MAPPINGS, TaskInclude.TEST_RESULTS},
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


@pytest.mark.asyncio
async def test_task_repository_constraints_and_base_delete_list(
    pg_session: AsyncSession,
) -> None:
    vacancy_repo = VacancyRepository(pg_session)
    webhook_repo = WebhookEventRepository(pg_session)
    repo = TaskRepository(pg_session)

    await repo.add(Task(external_id="dup-task", title="Task A"))
    await pg_session.commit()

    with pytest.raises(IntegrityError):
        await repo.add(Task(external_id="dup-task", title="Task B"))

    await pg_session.rollback()

    with pytest.raises(IntegrityError):
        await repo.add(
            Task(
                external_id="fk-task",
                title="Invalid",
                sub_competency_mappings=[
                    TaskSubCompetencyMapping(sub_competency_id=uuid4(), weight=1.0)
                ],
            )
        )

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    event = WebhookEvent(
        event_id="evt-base",
        vacancy_id=vacancy.id,
        candidate_external_id="candidate",
        task_external_id="task",
    )
    await webhook_repo.add(event)

    task = Task(external_id="task-base", title="Base task")
    await repo.add(task)
    await pg_session.commit()

    all_tasks = await repo.get_list()
    assert len(all_tasks) == 2

    await webhook_repo.delete(event.id)
    await repo.delete(task.id)
    await pg_session.commit()

    assert await pg_session.scalar(select(func.count()).select_from(TaskOrm)) == 1
    assert (
        await pg_session.scalar(select(func.count()).select_from(WebhookEventOrm)) == 0
    )
