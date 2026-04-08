from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from competency_system.application.ports.external_testing_system import (
    ExternalTaskRecord,
)
from competency_system.application.use_cases.task import SyncTasksUseCase
from competency_system.domain.value_objects.enums import TaskMappingStatus, TaskType
from tests.factories import TaskFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow, external_testing_gateway_mock, job_queue_mock):
    return SyncTasksUseCase(mock_uow, external_testing_gateway_mock, job_queue_mock)


@pytest.fixture
def external_record() -> ExternalTaskRecord:
    return ExternalTaskRecord(
        external_id="task-1",
        title="API task",
        description="Build endpoint",
        type=TaskType.CODE,
        tags=["api"],
    )


async def test_sync_tasks_use_case_creates_task_and_enqueues_mapping(
    use_case: SyncTasksUseCase,
    mock_uow,
    external_testing_gateway_mock,
    job_queue_mock,
    external_record: ExternalTaskRecord,
) -> None:
    start = datetime(2026, 4, 1, tzinfo=UTC)
    end = datetime(2026, 4, 2, tzinfo=UTC)
    external_testing_gateway_mock.list_tasks.return_value = [external_record]
    mock_uow.tasks.get_by_external_id.return_value = None
    job_queue_mock.enqueue.return_value = uuid4()

    result = await use_case.execute(start=start, end=end)

    assert len(result.synced_tasks) == 1
    assert result.synced_tasks[0].mapping_status == TaskMappingStatus.PENDING
    mock_uow.tasks.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()
    job_queue_mock.enqueue.assert_awaited_once()
    external_testing_gateway_mock.list_tasks.assert_awaited_once_with(
        start=start, end=end
    )


async def test_sync_tasks_use_case_updates_existing_task(
    use_case: SyncTasksUseCase,
    mock_uow,
    external_testing_gateway_mock,
    external_record: ExternalTaskRecord,
) -> None:
    start = datetime(2026, 4, 1, tzinfo=UTC)
    end = datetime(2026, 4, 2, tzinfo=UTC)
    existing = TaskFactory().make(
        {"external_id": external_record.external_id, "mapping_validated": True}
    )
    external_testing_gateway_mock.list_tasks.return_value = [external_record]
    mock_uow.tasks.get_by_external_id.return_value = existing

    result = await use_case.execute(start=start, end=end)

    assert len(result.synced_tasks) == 1
    assert result.synced_tasks[0].id == existing.id
    assert existing.mapping_validated is False
    external_testing_gateway_mock.list_tasks.assert_awaited_once_with(
        start=start, end=end
    )
