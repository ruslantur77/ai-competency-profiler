from __future__ import annotations

import pytest

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

    result = await use_case.execute()

    assert [item.external_id for item in result] == ["t-1", "t-2"]
    mock_uow.tasks.get_list.assert_awaited_once()


async def test_list_tasks_use_case_returns_empty_when_repository_empty(
    use_case: ListTasksUseCase, mock_uow
) -> None:
    mock_uow.tasks.get_list.return_value = []

    result = await use_case.execute()

    assert result == []
