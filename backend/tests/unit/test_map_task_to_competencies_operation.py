# ruff: noqa: E501
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.task import MapTaskToCompetenciesOperation
from competency_system.domain.entities import Category, SubCompetency
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

    with pytest.raises(NotFoundError, match="not found"):
        await operation.run(uuid4())


async def test_map_task_to_competencies_operation_marks_failed_when_mapping_raises(
    operation: MapTaskToCompetenciesOperation, mock_uow
) -> None:
    task = TaskFactory().make()
    mock_uow.tasks.get.return_value = task
    mock_uow.categories.get_list.return_value = [Category(name="Backend")]
    operation._map = AsyncMock(side_effect=RuntimeError("llm boom"))

    await operation.run(task.id)

    assert task.mapping_status == TaskMappingStatus.FAILED
    assert task.mapping_error_message == "llm boom"
    assert task.sub_competency_mappings == []
    assert task.mapping_validated is False
    mock_uow.tasks.add.assert_awaited_once_with(task)


async def test_map_task_to_competencies_operation_helper_methods_return_empty_for_missing_entities(
    operation: MapTaskToCompetenciesOperation, mock_uow
) -> None:
    mock_uow.categories.get.return_value = None
    mock_uow.competencies.get.return_value = None

    categories = await operation.competencies_by_category(uuid4())
    sub_competencies = await operation.sub_competencies_by_competency(uuid4())

    assert categories == []
    assert sub_competencies == []


def test_map_task_to_competencies_operation_normalize_mappings_sorts_and_limits() -> (
    None
):
    operation = MapTaskToCompetenciesOperation.__new__(MapTaskToCompetenciesOperation)
    operation._max_mappings = 2
    task_id = uuid4()
    sub_a = SubCompetency(name="A", weight=0.8)
    sub_b = SubCompetency(name="B", weight=0.2)
    sub_c = SubCompetency(name="C", weight=0.5)

    mappings = operation._normalize_mappings(task_id, [sub_a, sub_b, sub_c])

    assert len(mappings) == 2
    assert [item.sub_competency_id for item in mappings] == [sub_b.id, sub_c.id]
