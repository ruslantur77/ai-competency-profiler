from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.task import GetTaskGraphUseCase
from tests.factories import TaskFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return GetTaskGraphUseCase(mock_uow)


async def test_get_task_graph_use_case_returns_task(
    use_case: GetTaskGraphUseCase, mock_uow
) -> None:
    task = TaskFactory().make({"external_id": "task-42"})
    mock_uow.tasks.get.return_value = task

    result = await use_case.execute(task.id)

    assert result.id == task.id
    assert result.external_id == "task-42"
    mock_uow.tasks.get.assert_awaited_once()


async def test_get_task_graph_use_case_raises_when_task_not_found(
    use_case: GetTaskGraphUseCase, mock_uow
) -> None:
    mock_uow.tasks.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4())
