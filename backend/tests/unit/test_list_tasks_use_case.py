from __future__ import annotations

import pytest

from competency_system.application.ports.repositories import TaskInclude
from competency_system.application.use_cases.task import ListTasksUseCase
from tests.factories import TaskFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return ListTasksUseCase(mock_uow)


async def test_list_tasks_use_case_returns_mapped_tasks(
    use_case: ListTasksUseCase, mock_uow
) -> None:
    task_one = TaskFactory().make({"external_id": "t-1"})
    task_two = TaskFactory().make({"external_id": "t-2"})
    mock_uow.tasks.get_list.return_value = [task_one, task_two]
    mock_uow.tasks.count.return_value = 2

    result = await use_case.execute(limit=10, offset=0)

    assert [item.external_id for item in result.items] == ["t-1", "t-2"]
    assert result.total == 2
    mock_uow.tasks.get_list.assert_awaited_once_with(
        include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
        limit=10,
        offset=0,
    )


async def test_list_tasks_use_case_returns_empty_when_repository_empty(
    use_case: ListTasksUseCase, mock_uow
) -> None:
    mock_uow.tasks.get_list.return_value = []
    mock_uow.tasks.count.return_value = 0

    result = await use_case.execute(limit=10, offset=0)

    assert result.items == []
    assert result.total == 0
