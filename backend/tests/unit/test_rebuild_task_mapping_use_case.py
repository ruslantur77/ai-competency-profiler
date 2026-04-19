from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import TaskStatusUpdateDTO
from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.ports.repositories import TaskInclude
from competency_system.application.use_cases.task import UpdateTaskStatusUseCase
from competency_system.domain.value_objects.enums import TaskStatus
from tests.factories import (
    TaskCategoryNodeFactory,
    TaskCompetencyNodeFactory,
    TaskFactory,
    TaskSubCompetencyNodeFactory,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return UpdateTaskStatusUseCase(mock_uow)


async def test_update_task_status_use_case_allows_valid_transition(
    use_case: UpdateTaskStatusUseCase, mock_uow
) -> None:
    task = TaskFactory().make(
        {
            "status": TaskStatus.DRAFT,
            "category_nodes": [TaskCategoryNodeFactory().make()],
            "competency_nodes": [TaskCompetencyNodeFactory().make()],
            "sub_competency_nodes": [TaskSubCompetencyNodeFactory().make()],
        }
    )
    mock_uow.tasks.get.return_value = task

    result = await use_case.execute(
        task.id, TaskStatusUpdateDTO(status=TaskStatus.READY)
    )

    assert result.status == TaskStatus.READY
    assert len(task.category_nodes) > 0
    assert len(task.competency_nodes) > 0
    assert len(task.sub_competency_nodes) > 0
    mock_uow.tasks.get.assert_any_await(task.id, include={TaskInclude.NORMALIZED_GRAPH})
    mock_uow.tasks.add.assert_awaited_once_with(task)
    mock_uow.commit.assert_awaited_once()


async def test_update_task_status_use_case_rejects_invalid_transition(
    use_case: UpdateTaskStatusUseCase, mock_uow
) -> None:
    task = TaskFactory().make({"status": TaskStatus.READY})
    mock_uow.tasks.get.return_value = task

    with pytest.raises(ValidationError, match="Invalid status transition"):
        await use_case.execute(task.id, TaskStatusUpdateDTO(status=TaskStatus.PENDING))


async def test_update_task_status_use_case_raises_when_task_not_found(
    use_case: UpdateTaskStatusUseCase, mock_uow
) -> None:
    mock_uow.tasks.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4(), TaskStatusUpdateDTO(status=TaskStatus.DRAFT))
