from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.use_cases.task import FinalizeTaskGraphUseCase
from tests.factories import TaskFactory, TaskSubCompetencyNodeFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return FinalizeTaskGraphUseCase(mock_uow)


async def test_finalize_task_graph_use_case_marks_task_ready(
    use_case: FinalizeTaskGraphUseCase, mock_uow
) -> None:
    task = TaskFactory().make(
        {"sub_competency_nodes": [TaskSubCompetencyNodeFactory().make()]}
    )
    mock_uow.tasks.get.return_value = task

    result = await use_case.execute(task.id)

    assert result.status.value == "ready"
    mock_uow.tasks.add.assert_awaited_once_with(task)
    mock_uow.commit.assert_awaited_once()


async def test_finalize_task_graph_use_case_raises_when_task_not_found(
    use_case: FinalizeTaskGraphUseCase, mock_uow
) -> None:
    mock_uow.tasks.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4())


async def test_finalize_task_graph_use_case_requires_non_empty_graph(
    use_case: FinalizeTaskGraphUseCase, mock_uow
) -> None:
    task = TaskFactory().make({"sub_competency_nodes": []})
    mock_uow.tasks.get.return_value = task

    with pytest.raises(ValidationError, match="at least one sub-competency"):
        await use_case.execute(task.id)
