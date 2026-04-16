from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.task import ValidateTaskMappingUseCase
from tests.factories import TaskFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return ValidateTaskMappingUseCase(mock_uow)


async def test_validate_task_mapping_use_case_marks_task_validated(
    use_case: ValidateTaskMappingUseCase, mock_uow
) -> None:
    task = TaskFactory().make({"mapping_validated": False})
    mock_uow.tasks.get.return_value = task

    result = await use_case.execute(task.id)

    assert result.mapping_validated is True
    mock_uow.tasks.add.assert_awaited_once_with(task)
    mock_uow.commit.assert_awaited_once()


async def test_validate_task_mapping_use_case_raises_when_task_not_found(
    use_case: ValidateTaskMappingUseCase, mock_uow
) -> None:
    mock_uow.tasks.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4())
