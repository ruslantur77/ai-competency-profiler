from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import (
    TaskMappingReplaceDTO,
    TaskMappingReplaceItemDTO,
)
from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.use_cases.task import ReplaceTaskMappingUseCase
from tests.factories.domain import CompetencyFactory, SubCompetencyFactory, TaskFactory

pytestmark = pytest.mark.unit


async def test_replace_task_mapping_use_case_replaces_all_mappings(mock_uow) -> None:
    use_case = ReplaceTaskMappingUseCase(mock_uow)
    task = TaskFactory().make()
    competency = CompetencyFactory().make()
    sub = SubCompetencyFactory().make({"competency_id": competency.id})

    mock_uow.tasks.get.return_value = task
    mock_uow.sub_competencies.get.return_value = sub
    mock_uow.competencies.get.return_value = competency

    result = await use_case.execute(
        task.id,
        TaskMappingReplaceDTO(
            mappings=[
                TaskMappingReplaceItemDTO(
                    category_id=competency.category_id,
                    competency_id=competency.id,
                    sub_competency_id=sub.id,
                    weight=0.7,
                )
            ]
        ),
    )

    assert result.id == task.id
    assert len(task.sub_competency_mappings) == 1
    assert task.mapping_validated is True
    mock_uow.tasks.add.assert_awaited_once_with(task)
    mock_uow.commit.assert_awaited_once()


async def test_replace_task_mapping_use_case_raises_when_task_missing(mock_uow) -> None:
    use_case = ReplaceTaskMappingUseCase(mock_uow)
    mock_uow.tasks.get.return_value = None

    with pytest.raises(NotFoundError):
        await use_case.execute(
            task_id=uuid4(), command=TaskMappingReplaceDTO(mappings=[])
        )


async def test_replace_task_mapping_use_case_validates_hierarchy(mock_uow) -> None:
    use_case = ReplaceTaskMappingUseCase(mock_uow)
    task = TaskFactory().make()
    wrong_competency_id = uuid4()
    sub = SubCompetencyFactory().make()

    mock_uow.tasks.get.return_value = task
    mock_uow.sub_competencies.get.return_value = sub

    with pytest.raises(ValidationError):
        await use_case.execute(
            task.id,
            TaskMappingReplaceDTO(
                mappings=[
                    TaskMappingReplaceItemDTO(
                        category_id=uuid4(),
                        competency_id=wrong_competency_id,
                        sub_competency_id=sub.id,
                        weight=0.5,
                    )
                ]
            ),
        )
