from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.use_cases.task import MapTaskToCompetenciesOperation
from competency_system.domain.value_objects.enums import TaskMappingStatus
from tests.factories import TaskFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def operation(mock_uow, llm_gateway_mock):
    return MapTaskToCompetenciesOperation(llm_gateway_mock, mock_uow)


async def test_map_task_to_competencies_operation_marks_completed_on_success(
    operation: MapTaskToCompetenciesOperation, mock_uow
) -> None:
    task = TaskFactory().make()
    mock_uow.tasks.get.return_value = task
    mock_uow.categories.get_list.return_value = []

    await operation.run(task.id)

    assert task.mapping_status == TaskMappingStatus.COMPLETED
    assert task.mapping_error_message is None
    assert task.mapping_validated is False
    mock_uow.tasks.add.assert_awaited_once_with(task)
    mock_uow.commit.assert_awaited_once()


async def test_map_task_to_competencies_operation_raises_when_task_missing(
    operation: MapTaskToCompetenciesOperation, mock_uow
) -> None:
    mock_uow.tasks.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await operation.run(uuid4())
