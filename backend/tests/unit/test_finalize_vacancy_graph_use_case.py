from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import (
    VacancyGraphCategoryInputDTO,
    VacancyGraphCompetencyInputDTO,
    VacancyGraphSubCompetencyInputDTO,
    VacancyGraphUpdateDTO,
)
from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.use_cases.vacancy import (
    FinalizeVacancyGraphUseCase,
    SaveVacancyGraphUseCase,
)
from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return SaveVacancyGraphUseCase(mock_uow)


@pytest.fixture
def finalize_use_case(mock_uow):
    return FinalizeVacancyGraphUseCase(mock_uow)


@pytest.fixture
def graph_update() -> VacancyGraphUpdateDTO:
    sub_id = uuid4()
    return VacancyGraphUpdateDTO(
        categories=[
            VacancyGraphCategoryInputDTO(
                mode="new",
                temp_id=uuid4(),
                name="Engineering",
                description="Core",
                emoji="E",
                competencies=[
                    VacancyGraphCompetencyInputDTO(
                        mode="new",
                        temp_id=uuid4(),
                        name="Backend",
                        description="APIs",
                        is_required=True,
                        sub_competencies=[
                            VacancyGraphSubCompetencyInputDTO(
                                mode="new",
                                temp_id=sub_id,
                                name="REST",
                                description="HTTP APIs",
                                target_level=CompetencyLevel.ADVANCED,
                                weight=0.9,
                            )
                        ],
                    )
                ],
            )
        ],
    )


async def test_finalize_vacancy_graph_use_case_updates_graph_only(
    use_case: SaveVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    mock_uow.vacancies.get.return_value = vacancy

    result = await use_case.execute(vacancy.id, graph_update)

    assert result.status == VacancyStatus.DRAFT
    mock_uow.categories.add.assert_awaited()
    mock_uow.competencies.add.assert_awaited()
    mock_uow.sub_competencies.add.assert_awaited()
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_finalize_vacancy_graph_use_case_raises_when_vacancy_missing(
    use_case: SaveVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4(), graph_update)


async def test_finalize_vacancy_graph_use_case_does_not_touch_suggestions(
    use_case: SaveVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    mock_uow.vacancies.get.return_value = vacancy

    await use_case.execute(vacancy.id, graph_update)

    mock_uow.vacancy_suggestions.get.assert_not_awaited()
    mock_uow.vacancy_suggestions.list_by_vacancy.assert_not_awaited()
    mock_uow.vacancy_suggestions.add.assert_not_awaited()


async def test_finalize_vacancy_graph_use_case_sets_ready_status(
    finalize_use_case: FinalizeVacancyGraphUseCase,
    mock_uow,
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    mock_uow.vacancies.get.return_value = vacancy

    result = await finalize_use_case.execute(vacancy.id)

    assert result.status == VacancyStatus.READY
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_finalize_vacancy_graph_use_case_raises_when_vacancy_missing_on_finalize(
    finalize_use_case: FinalizeVacancyGraphUseCase,
    mock_uow,
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await finalize_use_case.execute(uuid4())


async def test_save_graph_accepts_mixed_existing_and_new_nodes(
    use_case: SaveVacancyGraphUseCase,
    mock_uow,
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    existing_category = Category(id=uuid4(), name="Data", description="", emoji="📊")
    existing_competency = Competency(
        id=uuid4(),
        category_id=existing_category.id,
        name="SQL",
        description="",
        sub_competencies=[],
    )
    existing_sub = SubCompetency(
        id=uuid4(),
        competency_id=existing_competency.id,
        name="Indexes",
        description="",
        weight=1.0,
        target_level=CompetencyLevel.INTERMEDIATE,
    )
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.categories.get.side_effect = lambda category_id: (
        existing_category if category_id == existing_category.id else None
    )
    mock_uow.competencies.get.side_effect = lambda competency_id: (
        existing_competency if competency_id == existing_competency.id else None
    )
    mock_uow.sub_competencies.get.side_effect = lambda sub_id: (
        existing_sub if sub_id == existing_sub.id else None
    )

    graph_update = VacancyGraphUpdateDTO(
        categories=[
            VacancyGraphCategoryInputDTO(
                mode="existing",
                id=existing_category.id,
                competencies=[
                    VacancyGraphCompetencyInputDTO(
                        mode="existing",
                        id=existing_competency.id,
                        is_required=True,
                        sub_competencies=[
                            VacancyGraphSubCompetencyInputDTO(
                                mode="existing",
                                id=existing_sub.id,
                                target_level=CompetencyLevel.ADVANCED,
                                weight=0.8,
                            ),
                            VacancyGraphSubCompetencyInputDTO(
                                mode="new",
                                temp_id=uuid4(),
                                name="Query planner",
                                description="",
                                target_level=CompetencyLevel.ADVANCED,
                                weight=0.6,
                            ),
                        ],
                    ),
                    VacancyGraphCompetencyInputDTO(
                        mode="new",
                        temp_id=uuid4(),
                        name="Data modeling",
                        description="",
                        is_required=False,
                        sub_competencies=[],
                    ),
                ],
            ),
            VacancyGraphCategoryInputDTO(
                mode="new",
                temp_id=uuid4(),
                name="Architecture",
                description="",
                emoji="🏗",
                competencies=[],
            ),
        ]
    )

    result = await use_case.execute(vacancy.id, graph_update)

    assert result.id == vacancy.id
    assert len(vacancy.category_nodes) == 2
    assert len(vacancy.competency_nodes) == 2
    assert len(vacancy.sub_competency_nodes) == 2
    mock_uow.categories.add.assert_awaited_once()
    mock_uow.competencies.add.assert_awaited_once()
    mock_uow.sub_competencies.add.assert_awaited_once()


async def test_save_graph_rejects_existing_competency_with_wrong_category(
    use_case: SaveVacancyGraphUseCase,
    mock_uow,
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    category = Category(id=uuid4(), name="Data", description="", emoji="📊")
    wrong_category = Category(id=uuid4(), name="Backend", description="", emoji="💻")
    competency = Competency(
        id=uuid4(),
        category_id=wrong_category.id,
        name="SQL",
        description="",
        sub_competencies=[],
    )
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.categories.get.return_value = category
    mock_uow.competencies.get.return_value = competency

    graph_update = VacancyGraphUpdateDTO(
        categories=[
            VacancyGraphCategoryInputDTO(
                mode="existing",
                id=category.id,
                competencies=[
                    VacancyGraphCompetencyInputDTO(
                        mode="existing",
                        id=competency.id,
                        is_required=True,
                        sub_competencies=[],
                    )
                ],
            )
        ]
    )

    with pytest.raises(
        ValidationError, match="does not belong to the selected category"
    ):
        await use_case.execute(vacancy.id, graph_update)
