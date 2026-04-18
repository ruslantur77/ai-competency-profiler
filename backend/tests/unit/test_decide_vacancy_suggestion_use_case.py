from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import VacancySuggestionDecisionDTO
from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.use_cases.vacancy import (
    DecideVacancySuggestionUseCase,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    SuggestionStage,
    SuggestionStatus,
)
from tests.factories import (
    CategoryFactory,
    CompetencyFactory,
    VacancyFactory,
    VacancyGraphSuggestionFactory,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return DecideVacancySuggestionUseCase(mock_uow)


async def test_decide_vacancy_suggestion_use_case_rejected_updates_status_only(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    suggestion = VacancyGraphSuggestionFactory().make(
        {"vacancy_id": vacancy.id, "status": SuggestionStatus.PENDING}
    )
    mock_uow.vacancy_suggestions.get.return_value = suggestion
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=suggestion.id, status=SuggestionStatus.REJECTED
    )

    result = await use_case.execute(vacancy.id, decision)

    assert result.status == SuggestionStatus.REJECTED
    mock_uow.vacancies.get.assert_awaited_once()
    mock_uow.categories.add.assert_not_awaited()
    mock_uow.vacancy_suggestions.add.assert_awaited_once_with(suggestion)
    mock_uow.commit.assert_awaited_once()


async def test_decide_vacancy_suggestion_use_case_rejects_pending_status(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=uuid4(), status=SuggestionStatus.PENDING
    )

    with pytest.raises(ValidationError, match="approved or rejected"):
        await use_case.execute(VacancyFactory().make().id, decision)


async def test_decide_vacancy_suggestion_use_case_raises_for_foreign_vacancy(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    current_vacancy = VacancyFactory().make()
    foreign_suggestion = VacancyGraphSuggestionFactory().make({"vacancy_id": uuid4()})
    mock_uow.vacancy_suggestions.get.return_value = foreign_suggestion
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=foreign_suggestion.id, status=SuggestionStatus.REJECTED
    )

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(current_vacancy.id, decision)


async def test_decide_vacancy_suggestion_use_case_approved_category_creates_node(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    suggestion = VacancyGraphSuggestionFactory().make(
        {"vacancy_id": vacancy.id, "status": SuggestionStatus.PENDING, "name": "Data"}
    )
    mock_uow.vacancy_suggestions.get.return_value = suggestion
    mock_uow.vacancies.get.return_value = vacancy
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=suggestion.id, status=SuggestionStatus.APPROVED
    )

    result = await use_case.execute(vacancy.id, decision)

    created_category = mock_uow.categories.add.await_args.args[0]
    assert result.status == SuggestionStatus.APPROVED
    assert created_category.name == "Data"
    assert len(vacancy.category_nodes) == 1
    assert vacancy.category_nodes[0].category_id == created_category.id
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_decide_vacancy_suggestion_use_case_approved_competency_adds_parent_nodes(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    parent_category = CategoryFactory().make()
    suggestion = VacancyGraphSuggestionFactory().make(
        {
            "vacancy_id": vacancy.id,
            "status": SuggestionStatus.PENDING,
            "stage": SuggestionStage.COMPETENCY,
            "name": "Caching",
            "parent_category_id": parent_category.id,
            "is_required": False,
        }
    )
    mock_uow.vacancy_suggestions.get.return_value = suggestion
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.categories.get.return_value = parent_category
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=suggestion.id, status=SuggestionStatus.APPROVED
    )

    await use_case.execute(vacancy.id, decision)

    created_competency = mock_uow.competencies.add.await_args.args[0]
    assert created_competency.name == "Caching"
    assert created_competency.category_id == parent_category.id
    assert len(vacancy.category_nodes) == 1
    assert vacancy.category_nodes[0].category_id == parent_category.id
    assert len(vacancy.competency_nodes) == 1
    assert vacancy.competency_nodes[0].competency_id == created_competency.id
    assert vacancy.competency_nodes[0].is_required is False


async def test_decide_approved_sub_competency_adds_parent_chain(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    parent_category = CategoryFactory().make()
    parent_competency = CompetencyFactory().make({"category_id": parent_category.id})
    suggestion = VacancyGraphSuggestionFactory().make(
        {
            "vacancy_id": vacancy.id,
            "status": SuggestionStatus.PENDING,
            "stage": SuggestionStage.SUB_COMPETENCY,
            "name": "Redis",
            "parent_competency_id": parent_competency.id,
            "target_level": CompetencyLevel.ADVANCED,
            "weight": 0.7,
        }
    )
    mock_uow.vacancy_suggestions.get.return_value = suggestion
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.competencies.get.return_value = parent_competency
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=suggestion.id, status=SuggestionStatus.APPROVED
    )

    await use_case.execute(vacancy.id, decision)

    created_sub = mock_uow.sub_competencies.add.await_args.args[0]
    assert created_sub.name == "Redis"
    assert created_sub.competency_id == parent_competency.id
    assert len(vacancy.category_nodes) == 1
    assert vacancy.category_nodes[0].category_id == parent_category.id
    assert len(vacancy.competency_nodes) == 1
    assert vacancy.competency_nodes[0].competency_id == parent_competency.id
    assert len(vacancy.sub_competency_nodes) == 1
    assert vacancy.sub_competency_nodes[0].sub_competency_id == created_sub.id
    assert vacancy.sub_competency_nodes[0].target_level == CompetencyLevel.ADVANCED
    assert vacancy.sub_competency_nodes[0].weight == pytest.approx(0.7)
