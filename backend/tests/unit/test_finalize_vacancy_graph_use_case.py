# ruff: noqa: E501
from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import (
    VacancyGraphCategoryInputDTO,
    VacancyGraphCompetencyInputDTO,
    VacancyGraphSubCompetencyInputDTO,
    VacancyGraphUpdateDTO,
    VacancySuggestionDecisionDTO,
)
from competency_system.application.use_cases.vacancy import (
    FinalizeVacancyGraphUseCase,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    VacancyStatus,
)
from tests.factories import VacancyFactory, VacancyGraphSuggestionFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return FinalizeVacancyGraphUseCase(mock_uow)


@pytest.fixture
def graph_update() -> VacancyGraphUpdateDTO:
    category_id = uuid4()
    competency_id = uuid4()
    sub_id = uuid4()
    suggestion_id = uuid4()
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
        suggestion_decisions=[
            VacancySuggestionDecisionDTO(
                suggestion_id=suggestion_id, status=SuggestionStatus.APPROVED
            )
        ],
    )


async def test_finalize_vacancy_graph_use_case_updates_graph_and_suggestions(
    use_case: FinalizeVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    suggestion = VacancyGraphSuggestionFactory().make(
        {
            "id": graph_update.suggestion_decisions[0].suggestion_id,
            "vacancy_id": vacancy.id,
            "stage": SuggestionStage.CATEGORY,
            "entity_type": SuggestionEntityType.CATEGORY,
            "name": "Engineering",
            "status": SuggestionStatus.PENDING,
        }
    )
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.vacancy_suggestions.get.return_value = suggestion
    mock_uow.vacancy_suggestions.list_by_vacancy.return_value = [suggestion]

    result = await use_case.execute(vacancy.id, graph_update)

    assert result.status == VacancyStatus.READY
    mock_uow.vacancy_suggestions.add.assert_awaited()
    mock_uow.categories.add.assert_awaited()
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_finalize_vacancy_graph_use_case_raises_when_vacancy_missing(
    use_case: FinalizeVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4(), graph_update)


async def test_finalize_vacancy_graph_use_case_skips_decision_for_foreign_suggestion(
    use_case: FinalizeVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    foreign = VacancyGraphSuggestionFactory().make(
        {
            "id": graph_update.suggestion_decisions[0].suggestion_id,
            "vacancy_id": uuid4(),
            "stage": SuggestionStage.CATEGORY,
            "entity_type": SuggestionEntityType.CATEGORY,
            "name": "Other",
            "status": SuggestionStatus.PENDING,
        }
    )
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.vacancy_suggestions.get.return_value = foreign
    mock_uow.vacancy_suggestions.list_by_vacancy.return_value = []

    await use_case.execute(vacancy.id, graph_update)

    mock_uow.vacancy_suggestions.add.assert_not_awaited()


async def test_finalize_vacancy_graph_use_case_auto_approves_stage_specific_pending_suggestions(
    use_case: FinalizeVacancyGraphUseCase, mock_uow, graph_update: VacancyGraphUpdateDTO
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.DRAFT})
    decision_target = VacancyGraphSuggestionFactory().make(
        {
            "id": graph_update.suggestion_decisions[0].suggestion_id,
            "vacancy_id": vacancy.id,
            "stage": SuggestionStage.CATEGORY,
            "entity_type": SuggestionEntityType.CATEGORY,
            "name": "Engineering",
            "status": SuggestionStatus.PENDING,
        }
    )
    pending_comp = VacancyGraphSuggestionFactory().make(
        {
            "vacancy_id": vacancy.id,
            "stage": SuggestionStage.COMPETENCY,
            "entity_type": SuggestionEntityType.COMPETENCY,
            "name": "Backend",
            "status": SuggestionStatus.PENDING,
        }
    )
    pending_sub = VacancyGraphSuggestionFactory().make(
        {
            "vacancy_id": vacancy.id,
            "stage": SuggestionStage.SUB_COMPETENCY,
            "entity_type": SuggestionEntityType.SUB_COMPETENCY,
            "name": "REST",
            "status": SuggestionStatus.PENDING,
        }
    )
    rejected = VacancyGraphSuggestionFactory().make(
        {
            "vacancy_id": vacancy.id,
            "stage": SuggestionStage.CATEGORY,
            "entity_type": SuggestionEntityType.CATEGORY,
            "name": "Engineering",
            "status": SuggestionStatus.REJECTED,
        }
    )
    mismatch = VacancyGraphSuggestionFactory().make(
        {
            "vacancy_id": vacancy.id,
            "stage": SuggestionStage.COMPETENCY,
            "entity_type": SuggestionEntityType.COMPETENCY,
            "name": "Other",
            "status": SuggestionStatus.PENDING,
        }
    )
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.vacancy_suggestions.get.return_value = decision_target
    mock_uow.vacancy_suggestions.list_by_vacancy.return_value = [
        pending_comp,
        pending_sub,
        rejected,
        mismatch,
    ]

    await use_case.execute(vacancy.id, graph_update)

    assert pending_comp.status == SuggestionStatus.APPROVED
    assert pending_sub.status == SuggestionStatus.APPROVED
    assert rejected.status == SuggestionStatus.REJECTED
    assert mismatch.status == SuggestionStatus.PENDING
