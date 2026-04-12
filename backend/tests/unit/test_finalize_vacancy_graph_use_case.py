from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import (
    VacancyGraphCategoryInputDTO,
    VacancyGraphCompetencyInputDTO,
    VacancyGraphSubCompetencyInputDTO,
    VacancyGraphUpdateDTO,
)
from competency_system.application.use_cases.vacancy import FinalizeVacancyGraphUseCase
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return FinalizeVacancyGraphUseCase(mock_uow)


@pytest.fixture
def graph_update() -> VacancyGraphUpdateDTO:
    category_id = uuid4()
    competency_id = uuid4()
    sub_id = uuid4()
    return VacancyGraphUpdateDTO(
        categories=[
            VacancyGraphCategoryInputDTO(
                id=category_id,
                name="Engineering",
                description="Core",
                emoji="E",
                competencies=[
                    VacancyGraphCompetencyInputDTO(
                        id=competency_id,
                        category_id=category_id,
                        name="Backend",
                        description="APIs",
                        is_required=True,
                        sub_competencies=[
                            VacancyGraphSubCompetencyInputDTO(
                                id=sub_id,
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
    use_case: FinalizeVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    mock_uow.vacancies.get.return_value = vacancy

    result = await use_case.execute(vacancy.id, graph_update)

    assert result.status == VacancyStatus.READY
    mock_uow.categories.add.assert_awaited()
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_finalize_vacancy_graph_use_case_raises_when_vacancy_missing(
    use_case: FinalizeVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4(), graph_update)


async def test_finalize_vacancy_graph_use_case_does_not_touch_suggestions(
    use_case: FinalizeVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    mock_uow.vacancies.get.return_value = vacancy

    await use_case.execute(vacancy.id, graph_update)

    mock_uow.vacancy_suggestions.get.assert_not_awaited()
    mock_uow.vacancy_suggestions.list_by_vacancy.assert_not_awaited()
    mock_uow.vacancy_suggestions.add.assert_not_awaited()
