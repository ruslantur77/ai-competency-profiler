from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import (
    VacancySuggestionBulkDecisionDTO,
    VacancySuggestionDecisionDTO,
)
from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.vacancy import (
    DecideVacancySuggestionsUseCase,
)
from competency_system.domain.value_objects.enums import (
    SuggestionStage,
    SuggestionStatus,
)
from tests.factories import (
    CategoryFactory,
    VacancyFactory,
    VacancyGraphSuggestionFactory,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return DecideVacancySuggestionsUseCase(mock_uow)


async def test_bulk_decide_rejected_updates_all_and_commits_once(
    use_case: DecideVacancySuggestionsUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    suggestion_1 = VacancyGraphSuggestionFactory().make(
        {"vacancy_id": vacancy.id, "status": SuggestionStatus.PENDING}
    )
    suggestion_2 = VacancyGraphSuggestionFactory().make(
        {"vacancy_id": vacancy.id, "status": SuggestionStatus.PENDING}
    )
    mock_uow.vacancy_suggestions.get.side_effect = [suggestion_1, suggestion_2]

    command = VacancySuggestionBulkDecisionDTO(
        decisions=[
            VacancySuggestionDecisionDTO(
                suggestion_id=suggestion_1.id,
                status=SuggestionStatus.REJECTED,
            ),
            VacancySuggestionDecisionDTO(
                suggestion_id=suggestion_2.id,
                status=SuggestionStatus.REJECTED,
            ),
        ]
    )

    result = await use_case.execute(vacancy.id, command)

    assert len(result) == 2
    assert result[0].status == SuggestionStatus.REJECTED
    assert result[1].status == SuggestionStatus.REJECTED
    assert mock_uow.vacancy_suggestions.add.await_count == 2
    mock_uow.vacancies.get.assert_awaited_once()
    mock_uow.vacancies.add.assert_not_awaited()
    mock_uow.commit.assert_awaited_once()


async def test_bulk_decide_approved_loads_vacancy_once_and_applies(
    use_case: DecideVacancySuggestionsUseCase, mock_uow
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
            "is_required": True,
        }
    )
    mock_uow.vacancy_suggestions.get.return_value = suggestion
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.categories.get.return_value = parent_category

    command = VacancySuggestionBulkDecisionDTO(
        decisions=[
            VacancySuggestionDecisionDTO(
                suggestion_id=suggestion.id,
                status=SuggestionStatus.APPROVED,
            )
        ]
    )

    result = await use_case.execute(vacancy.id, command)

    assert len(result) == 1
    assert result[0].status == SuggestionStatus.APPROVED
    assert mock_uow.vacancies.get.await_count == 2
    mock_uow.competencies.add.assert_awaited_once()
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_bulk_decide_raises_when_foreign_suggestion(
    use_case: DecideVacancySuggestionsUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    foreign = VacancyGraphSuggestionFactory().make({"vacancy_id": uuid4()})
    mock_uow.vacancy_suggestions.get.return_value = foreign

    command = VacancySuggestionBulkDecisionDTO(
        decisions=[
            VacancySuggestionDecisionDTO(
                suggestion_id=foreign.id,
                status=SuggestionStatus.REJECTED,
            )
        ]
    )

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(vacancy.id, command)

    mock_uow.commit.assert_not_awaited()
