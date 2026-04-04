from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import VacancySuggestionDecisionDTO
from competency_system.application.use_cases.vacancy import (
    DecideVacancySuggestionUseCase,
)
from competency_system.domain.value_objects.enums import SuggestionStatus
from tests.factories import VacancyFactory, VacancyGraphSuggestionFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return DecideVacancySuggestionUseCase(mock_uow)


async def test_decide_vacancy_suggestion_use_case_updates_status(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make()
    suggestion = VacancyGraphSuggestionFactory().make(
        {"vacancy_id": vacancy.id, "status": SuggestionStatus.PENDING}
    )
    mock_uow.vacancy_suggestions.get.return_value = suggestion
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=suggestion.id, status=SuggestionStatus.APPROVED
    )

    result = await use_case.execute(vacancy.id, decision)

    assert result.status == SuggestionStatus.APPROVED
    mock_uow.vacancy_suggestions.add.assert_awaited_once_with(suggestion)
    mock_uow.commit.assert_awaited_once()


async def test_decide_vacancy_suggestion_use_case_rejects_pending_status(
    use_case: DecideVacancySuggestionUseCase, mock_uow
) -> None:
    decision = VacancySuggestionDecisionDTO(
        suggestion_id=uuid4(), status=SuggestionStatus.PENDING
    )

    with pytest.raises(ValueError, match="approved or rejected"):
        await use_case.execute(VacancyFactory().make().id, decision)
