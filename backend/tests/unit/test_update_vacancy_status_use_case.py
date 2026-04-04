from __future__ import annotations

import pytest

from competency_system.application.dtos.vacancy import VacancyStatusUpdateDTO
from competency_system.application.use_cases.vacancy import UpdateVacancyStatusUseCase
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return UpdateVacancyStatusUseCase(mock_uow)


async def test_update_vacancy_status_use_case_changes_status_on_allowed_transition(
    use_case: UpdateVacancyStatusUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make(
        {"status": VacancyStatus.DRAFT, "error_message": "old error"}
    )
    mock_uow.vacancies.get.return_value = vacancy

    result = await use_case.execute(
        vacancy.id, VacancyStatusUpdateDTO(status=VacancyStatus.READY)
    )

    assert result.status == VacancyStatus.READY
    assert vacancy.error_message is None
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_update_vacancy_status_use_case_rejects_invalid_transition(
    use_case: UpdateVacancyStatusUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.READY})
    mock_uow.vacancies.get.return_value = vacancy

    with pytest.raises(ValueError, match="Invalid status transition"):
        await use_case.execute(
            vacancy.id, VacancyStatusUpdateDTO(status=VacancyStatus.PENDING)
        )
