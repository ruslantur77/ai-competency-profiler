from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import (
    TaskGraphCategoryInputDTO,
    TaskGraphCompetencyInputDTO,
    TaskGraphSubCompetencyInputDTO,
)
from competency_system.application.errors import ValidationError
from competency_system.application.use_cases.graph_builder import GraphEntityResolver
from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.domain.value_objects.competency_level import CompetencyLevel

pytestmark = pytest.mark.unit


async def test_graph_entity_resolver_creates_new_nodes(mock_uow) -> None:
    resolver = GraphEntityResolver()
    payload = await resolver.resolve(
        mock_uow,
        [
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
    )

    assert len(payload.categories_to_create) == 1
    assert len(payload.competencies_to_create) == 1
    assert len(payload.sub_competencies_to_create) == 1
    assert len(payload.categories) == 1
    assert len(payload.competencies) == 1
    assert len(payload.sub_competencies) == 1
    assert payload.categories[0].position == 0
    assert payload.competencies[0].position == 0
    assert payload.sub_competencies[0].position == 0


async def test_graph_entity_resolver_rejects_existing_competency_with_wrong_category(
    mock_uow,
) -> None:
    resolver = GraphEntityResolver()
    category = Category(id=uuid4(), name="Data", description="", emoji="D")
    wrong_category = Category(id=uuid4(), name="Backend", description="", emoji="B")
    competency = Competency(
        id=uuid4(),
        category_id=wrong_category.id,
        name="SQL",
        description="",
        sub_competencies=[],
    )
    mock_uow.categories.get.return_value = category
    mock_uow.competencies.get.return_value = competency

    with pytest.raises(ValidationError, match="selected category"):
        await resolver.resolve(
            mock_uow,
            [
                TaskGraphCategoryInputDTO(
                    mode="existing",
                    id=category.id,
                    competencies=[
                        TaskGraphCompetencyInputDTO(
                            mode="existing",
                            id=competency.id,
                            is_required=True,
                            sub_competencies=[],
                        )
                    ],
                )
            ],
        )


async def test_graph_entity_resolver_rejects_duplicate_competency_nodes(
    mock_uow,
) -> None:
    resolver = GraphEntityResolver()
    category = Category(id=uuid4(), name="Data", description="", emoji="D")
    competency = Competency(
        id=uuid4(),
        category_id=category.id,
        name="SQL",
        description="",
        sub_competencies=[],
    )
    mock_uow.categories.get.return_value = category
    mock_uow.competencies.get.return_value = competency

    with pytest.raises(ValidationError, match="Duplicate competency node"):
        await resolver.resolve(
            mock_uow,
            [
                TaskGraphCategoryInputDTO(
                    mode="existing",
                    id=category.id,
                    competencies=[
                        TaskGraphCompetencyInputDTO(
                            mode="existing",
                            id=competency.id,
                            is_required=True,
                            sub_competencies=[],
                        ),
                        TaskGraphCompetencyInputDTO(
                            mode="existing",
                            id=competency.id,
                            is_required=False,
                            sub_competencies=[],
                        ),
                    ],
                )
            ],
        )


async def test_graph_entity_resolver_rejects_duplicate_sub_competency_nodes(
    mock_uow,
) -> None:
    resolver = GraphEntityResolver()
    category = Category(id=uuid4(), name="Data", description="", emoji="D")
    competency = Competency(
        id=uuid4(),
        category_id=category.id,
        name="SQL",
        description="",
        sub_competencies=[],
    )
    sub_competency = SubCompetency(
        id=uuid4(),
        competency_id=competency.id,
        name="Indexes",
        description="",
        weight=1.0,
        target_level=CompetencyLevel.INTERMEDIATE,
    )
    mock_uow.categories.get.return_value = category
    mock_uow.competencies.get.return_value = competency
    mock_uow.sub_competencies.get.return_value = sub_competency

    with pytest.raises(ValidationError, match="Duplicate sub-competency node"):
        await resolver.resolve(
            mock_uow,
            [
                TaskGraphCategoryInputDTO(
                    mode="existing",
                    id=category.id,
                    competencies=[
                        TaskGraphCompetencyInputDTO(
                            mode="existing",
                            id=competency.id,
                            is_required=True,
                            sub_competencies=[
                                TaskGraphSubCompetencyInputDTO(
                                    mode="existing",
                                    id=sub_competency.id,
                                    target_level=CompetencyLevel.ADVANCED,
                                    weight=0.8,
                                ),
                                TaskGraphSubCompetencyInputDTO(
                                    mode="existing",
                                    id=sub_competency.id,
                                    target_level=CompetencyLevel.BEGINNER,
                                    weight=0.2,
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
