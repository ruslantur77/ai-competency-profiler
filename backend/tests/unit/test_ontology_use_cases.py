from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.competency import (
    CategoryCreateDTO,
    CategoryUpdateDTO,
    CompetencyCreateDTO,
    CompetencyUpdateDTO,
    SubCompetencyCreateDTO,
    SubCompetencyUpdateDTO,
)
from competency_system.application.ports.repositories import CategoryInclude
from competency_system.application.use_cases.ontology import (
    CreateCategoryUseCase,
    CreateCompetencyUseCase,
    CreateSubCompetencyUseCase,
    ListCategoriesUseCase,
    UpdateCategoryUseCase,
    UpdateCompetencyUseCase,
    UpdateSubCompetencyUseCase,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from tests.factories import CategoryFactory, CompetencyFactory, SubCompetencyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def list_categories_use_case(mock_uow):
    return ListCategoriesUseCase(uow=mock_uow)


@pytest.fixture
def create_category_use_case(mock_uow):
    return CreateCategoryUseCase(uow=mock_uow)


@pytest.fixture
def update_category_use_case(mock_uow):
    return UpdateCategoryUseCase(uow=mock_uow)


@pytest.fixture
def create_competency_use_case(mock_uow):
    return CreateCompetencyUseCase(uow=mock_uow)


@pytest.fixture
def update_competency_use_case(mock_uow):
    return UpdateCompetencyUseCase(uow=mock_uow)


@pytest.fixture
def create_sub_competency_use_case(mock_uow):
    return CreateSubCompetencyUseCase(uow=mock_uow)


@pytest.fixture
def update_sub_competency_use_case(mock_uow):
    return UpdateSubCompetencyUseCase(uow=mock_uow)


async def test_list_categories_use_case_loads_full_tree(
    list_categories_use_case: ListCategoriesUseCase, mock_uow
) -> None:
    category = CategoryFactory().make()
    mock_uow.categories.get_list.return_value = [category]

    result = await list_categories_use_case.execute()

    assert len(result) == 1
    mock_uow.categories.get_list.assert_awaited_once_with(
        include={CategoryInclude.SUB_COMPETENCIES}
    )


async def test_create_category_use_case_persists_entity(
    create_category_use_case: CreateCategoryUseCase, mock_uow
) -> None:
    command = CategoryCreateDTO(name="Data", description="Data skills", emoji="📊")

    result = await create_category_use_case.execute(command)

    assert result.name == "Data"
    assert result.emoji == "📊"
    mock_uow.categories.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


async def test_update_category_use_case_raises_when_not_found(
    update_category_use_case: UpdateCategoryUseCase, mock_uow
) -> None:
    mock_uow.categories.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await update_category_use_case.execute(
            uuid4(),
            CategoryUpdateDTO(name="Updated"),
        )
    mock_uow.commit.assert_not_awaited()


async def test_create_competency_use_case_validates_parent_category(
    create_competency_use_case: CreateCompetencyUseCase, mock_uow
) -> None:
    mock_uow.categories.get.return_value = None

    with pytest.raises(ValueError, match="Category .* not found"):
        await create_competency_use_case.execute(
            CompetencyCreateDTO(
                category_id=uuid4(),
                name="Backend",
                description="",
            )
        )
    mock_uow.competencies.add.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


async def test_update_competency_use_case_updates_fields(
    update_competency_use_case: UpdateCompetencyUseCase, mock_uow
) -> None:
    category = CategoryFactory().make()
    competency = CompetencyFactory().make({"category_id": category.id, "name": "Old"})
    target_category = CategoryFactory().make()

    mock_uow.competencies.get.return_value = competency
    mock_uow.categories.get.return_value = target_category

    result = await update_competency_use_case.execute(
        competency.id,
        CompetencyUpdateDTO(
            category_id=target_category.id,
            name="New",
            description="Updated",
        ),
    )

    assert result.name == "New"
    assert result.category_id == target_category.id
    mock_uow.competencies.add.assert_awaited_once_with(competency)
    mock_uow.commit.assert_awaited_once()


async def test_create_sub_competency_use_case_validates_parent_competency(
    create_sub_competency_use_case: CreateSubCompetencyUseCase, mock_uow
) -> None:
    mock_uow.competencies.get.return_value = None

    with pytest.raises(ValueError, match="Competency .* not found"):
        await create_sub_competency_use_case.execute(
            SubCompetencyCreateDTO(
                competency_id=uuid4(),
                name="REST",
                description="",
                weight=1.0,
                target_level=CompetencyLevel.INTERMEDIATE,
            )
        )
    mock_uow.sub_competencies.add.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


async def test_update_sub_competency_use_case_updates_fields(
    update_sub_competency_use_case: UpdateSubCompetencyUseCase, mock_uow
) -> None:
    competency = CompetencyFactory().make()
    updated_parent = CompetencyFactory().make()
    sub = SubCompetencyFactory().make({"competency_id": competency.id, "name": "Old"})

    mock_uow.sub_competencies.get.return_value = sub
    mock_uow.competencies.get.return_value = updated_parent

    result = await update_sub_competency_use_case.execute(
        sub.id,
        SubCompetencyUpdateDTO(
            competency_id=updated_parent.id,
            name="New",
            description="Updated",
            weight=0.6,
            target_level=CompetencyLevel.ADVANCED,
        ),
    )

    assert result.name == "New"
    assert result.competency_id == updated_parent.id
    assert result.weight == 0.6
    assert result.target_level == CompetencyLevel.ADVANCED
    mock_uow.sub_competencies.add.assert_awaited_once_with(sub)
    mock_uow.commit.assert_awaited_once()
