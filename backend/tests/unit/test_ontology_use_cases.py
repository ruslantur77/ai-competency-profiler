from __future__ import annotations

from types import SimpleNamespace
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
from competency_system.application.errors import ConflictError, NotFoundError
from competency_system.application.ports.repositories import (
    CandidateInclude,
    CategoryInclude,
    CompetencyInclude,
    TaskInclude,
    VacancyInclude,
)
from competency_system.application.use_cases.ontology import (
    CreateCategoryUseCase,
    CreateCompetencyUseCase,
    CreateSubCompetencyUseCase,
    DeleteCategoryUseCase,
    DeleteCompetencyUseCase,
    DeleteSubCompetencyUseCase,
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


@pytest.fixture
def delete_category_use_case(mock_uow):
    return DeleteCategoryUseCase(uow=mock_uow)


@pytest.fixture
def delete_competency_use_case(mock_uow):
    return DeleteCompetencyUseCase(uow=mock_uow)


@pytest.fixture
def delete_sub_competency_use_case(mock_uow):
    return DeleteSubCompetencyUseCase(uow=mock_uow)


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


async def test_delete_category_use_case_conflict_when_has_competencies(
    delete_category_use_case: DeleteCategoryUseCase, mock_uow
) -> None:
    category = CategoryFactory().make(
        {"competencies": [CompetencyFactory().make({"category_id": uuid4()})]}
    )
    mock_uow.categories.get.return_value = category

    with pytest.raises(ConflictError, match="dependent competencies"):
        await delete_category_use_case.execute(category.id)
    mock_uow.categories.get.assert_awaited_once_with(
        category.id, include={CategoryInclude.COMPETENCIES}
    )
    mock_uow.categories.delete.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


async def test_delete_category_use_case_not_found(
    delete_category_use_case: DeleteCategoryUseCase, mock_uow
) -> None:
    mock_uow.categories.get.return_value = None

    with pytest.raises(NotFoundError, match="Category .* not found"):
        await delete_category_use_case.execute(uuid4())
    mock_uow.categories.delete.assert_not_awaited()


async def test_delete_competency_use_case_success(
    delete_competency_use_case: DeleteCompetencyUseCase, mock_uow
) -> None:
    competency = CompetencyFactory().make({"sub_competencies": []})
    mock_uow.competencies.get.return_value = competency
    mock_uow.vacancies.get_list.return_value = []

    await delete_competency_use_case.execute(competency.id)

    mock_uow.competencies.get.assert_awaited_once_with(
        competency.id, include={CompetencyInclude.SUB_COMPETENCIES}
    )
    mock_uow.vacancies.get_list.assert_awaited_once_with(
        include={VacancyInclude.NORMALIZED_GRAPH}
    )
    mock_uow.competencies.delete.assert_awaited_once_with(competency.id)
    mock_uow.commit.assert_awaited_once()


async def test_delete_competency_use_case_conflict_when_used_in_vacancy_graph(
    delete_competency_use_case: DeleteCompetencyUseCase, mock_uow
) -> None:
    competency = CompetencyFactory().make({"sub_competencies": []})
    mock_uow.competencies.get.return_value = competency
    mock_uow.vacancies.get_list.return_value = [
        SimpleNamespace(
            competency_nodes=[SimpleNamespace(competency_id=competency.id)],
            sub_competency_nodes=[],
        )
    ]

    with pytest.raises(ConflictError, match="used in vacancy graph"):
        await delete_competency_use_case.execute(competency.id)
    mock_uow.competencies.delete.assert_not_awaited()


async def test_delete_sub_competency_use_case_conflict_when_used_in_task_mapping(
    delete_sub_competency_use_case: DeleteSubCompetencyUseCase, mock_uow
) -> None:
    sub = SubCompetencyFactory().make()
    task = SimpleNamespace(
        sub_competency_mappings=[SimpleNamespace(sub_competency_id=sub.id)]
    )
    mock_uow.sub_competencies.get.return_value = sub
    mock_uow.tasks.get_list.return_value = [task]

    with pytest.raises(ConflictError, match="task mappings"):
        await delete_sub_competency_use_case.execute(sub.id)
    mock_uow.tasks.get_list.assert_awaited_once_with(
        include={TaskInclude.SUB_COMPETENCY_MAPPINGS}
    )
    mock_uow.sub_competencies.delete.assert_not_awaited()


async def test_delete_sub_competency_use_case_success(
    delete_sub_competency_use_case: DeleteSubCompetencyUseCase, mock_uow
) -> None:
    sub = SubCompetencyFactory().make()
    mock_uow.sub_competencies.get.return_value = sub
    mock_uow.tasks.get_list.return_value = []
    mock_uow.candidates.get_list.return_value = []
    mock_uow.vacancies.get_list.return_value = []

    await delete_sub_competency_use_case.execute(sub.id)

    mock_uow.tasks.get_list.assert_awaited_once_with(
        include={TaskInclude.SUB_COMPETENCY_MAPPINGS}
    )
    mock_uow.candidates.get_list.assert_awaited_once_with(
        include={CandidateInclude.ACHIEVEMENTS}
    )
    mock_uow.vacancies.get_list.assert_awaited_once_with(
        include={VacancyInclude.NORMALIZED_GRAPH}
    )
    mock_uow.sub_competencies.delete.assert_awaited_once_with(sub.id)
    mock_uow.commit.assert_awaited_once()
