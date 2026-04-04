from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.use_cases.task import RebuildTaskMappingUseCase
from competency_system.domain.value_objects.enums import TaskMappingStatus
from tests.factories import TaskFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow, llm_gateway_mock, job_queue_mock):
    return RebuildTaskMappingUseCase(mock_uow, llm_gateway_mock, job_queue_mock)


async def test_rebuild_task_mapping_use_case_marks_pending_and_enqueues(
    use_case: RebuildTaskMappingUseCase, mock_uow, job_queue_mock
) -> None:
    task = TaskFactory().make({"mapping_status": TaskMappingStatus.COMPLETED})
    mock_uow.tasks.get.return_value = task

    result = await use_case.execute(task.id)

    assert result.id == task.id
    assert task.mapping_status == TaskMappingStatus.PENDING
    assert task.mapping_validated is False
    mock_uow.tasks.add.assert_awaited_once_with(task)
    mock_uow.commit.assert_awaited_once()
    job_queue_mock.enqueue.assert_awaited_once()


async def test_rebuild_task_mapping_use_case_raises_when_task_not_found(
    use_case: RebuildTaskMappingUseCase, mock_uow
) -> None:
    mock_uow.tasks.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4())
