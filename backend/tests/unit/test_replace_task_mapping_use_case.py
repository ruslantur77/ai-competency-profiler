from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import (
    TaskGraphCategoryInputDTO,
    TaskGraphCompetencyInputDTO,
    TaskGraphSubCompetencyInputDTO,
    TaskGraphUpdateDTO,
)
from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.use_cases.task import SaveTaskGraphUseCase
from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from tests.factories import TaskFactory

pytestmark = pytest.mark.unit


async def test_save_task_graph_use_case_replaces_graph(mock_uow) -> None:
    use_case = SaveTaskGraphUseCase(mock_uow)
    task = TaskFactory().make()
    mock_uow.tasks.get.return_value = task

    result = await use_case.execute(
        task.id,
        TaskGraphUpdateDTO(
            categories=[
                TaskGraphCategoryInputDTO(
                    mode="new",
                    temp_id=uuid4(),
                    name="Engineering",
                    description="Core",
                    emoji="E",
                    competencies=[
                        TaskGraphCompetencyInputDTO(
                            mode="new",
                            temp_id=uuid4(),
                            name="Backend",
                            description="APIs",
                            is_required=True,
                            sub_competencies=[
                                TaskGraphSubCompetencyInputDTO(
                                    mode="new",
                                    temp_id=uuid4(),
                                    name="REST",
                                    description="HTTP APIs",
                                    target_level=CompetencyLevel.ADVANCED,
                                    weight=0.7,
                                )
                            ],
                        )
                    ],
                )
            ],
        ),
    )

    assert result.id == task.id
    assert len(task.category_nodes) == 1
    assert len(task.competency_nodes) == 1
    assert len(task.sub_competency_nodes) == 1
    mock_uow.tasks.add.assert_awaited_once_with(task)
    mock_uow.commit.assert_awaited_once()


async def test_save_task_graph_use_case_raises_when_task_missing(mock_uow) -> None:
    use_case = SaveTaskGraphUseCase(mock_uow)
    mock_uow.tasks.get.return_value = None

    with pytest.raises(NotFoundError):
        await use_case.execute(task_id=uuid4(), graph=TaskGraphUpdateDTO(categories=[]))


async def test_save_task_graph_use_case_validates_existing_hierarchy(mock_uow) -> None:
    use_case = SaveTaskGraphUseCase(mock_uow)
    task = TaskFactory().make()
    category = Category(id=uuid4(), name="Data", description="", emoji="D")
    wrong_competency = Competency(
        id=uuid4(),
        category_id=uuid4(),
        name="Backend",
        description="",
        sub_competencies=[],
    )
    sub = SubCompetency(
        id=uuid4(),
        competency_id=wrong_competency.id,
        name="REST",
        description="",
        weight=1.0,
        target_level=CompetencyLevel.BEGINNER,
    )
    mock_uow.tasks.get.return_value = task
    mock_uow.categories.get.return_value = category
    mock_uow.competencies.get.return_value = wrong_competency
    mock_uow.sub_competencies.get.return_value = sub

    with pytest.raises(ValidationError, match="selected category"):
        await use_case.execute(
            task.id,
            TaskGraphUpdateDTO(
                categories=[
                    TaskGraphCategoryInputDTO(
                        mode="existing",
                        id=category.id,
                        competencies=[
                            TaskGraphCompetencyInputDTO(
                                mode="existing",
                                id=wrong_competency.id,
                                is_required=True,
                                sub_competencies=[],
                            )
                        ],
                    )
                ],
            ),
        )
