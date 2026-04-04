from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import TaskDTO
from competency_system.application.ports.external_testing_system import (
    ExternalTaskRecord,
    ExternalTestingSystemGateway,
)
from competency_system.application.use_cases.task import (
    GetTaskUseCase,
    SyncTasksUseCase,
    ValidateTaskMappingUseCase,
)
from competency_system.domain.entities import Task
from competency_system.domain.value_objects.enums import TaskMappingStatus, TaskType

pytestmark = pytest.mark.unit


class FakeTestingGateway(ExternalTestingSystemGateway):
    def __init__(self, tasks: list[ExternalTaskRecord]) -> None:
        self._tasks = tasks

    async def list_tasks(self) -> list[ExternalTaskRecord]:
        return self._tasks


class _JobQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict[str, object]]] = []

    async def enqueue(self, *, job_type, payload: dict[str, object]):  # type: ignore[no-untyped-def]
        self.enqueued.append((job_type.value, payload))
        return uuid4()


@pytest.mark.asyncio
async def test_sync_tasks_use_case_marks_task_pending_and_enqueues_job(
    mock_uow,
) -> None:
    gateway = FakeTestingGateway(
        [
            ExternalTaskRecord(
                external_id="task-sync-1",
                title="API task",
                description="Build and persist data",
                type=TaskType.CODE,
                tags=["json", "sql"],
            )
        ]
    )
    queue = _JobQueue()
    mock_uow.tasks.get_by_external_id.return_value = None

    result = await SyncTasksUseCase(mock_uow, gateway, queue).execute()

    assert len(result.synced_tasks) == 1
    dto = result.synced_tasks[0]
    assert isinstance(dto, TaskDTO)
    assert dto.external_id == "task-sync-1"
    assert dto.mapping_status == TaskMappingStatus.PENDING
    assert dto.mapping_validated is False
    mock_uow.tasks.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()
    assert len(queue.enqueued) == 1


@pytest.mark.asyncio
async def test_validate_task_mapping_use_case_marks_task_validated(mock_uow) -> None:
    task = Task(
        external_id="task-1",
        title="Title",
        description="Desc",
        type=TaskType.CODE,
        mapping_validated=False,
    )
    mock_uow.tasks.get.return_value = task

    result = await ValidateTaskMappingUseCase(mock_uow).execute(task.id)

    assert result.mapping_validated is True
    mock_uow.tasks.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_task_use_case_raises_when_task_not_found(mock_uow) -> None:
    mock_uow.tasks.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await GetTaskUseCase(mock_uow).execute(uuid4())
