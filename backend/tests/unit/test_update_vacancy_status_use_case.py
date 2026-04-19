from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import VacancyStatusUpdateDTO
from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.ports.repositories import VacancyInclude
from competency_system.application.use_cases.vacancy import UpdateVacancyStatusUseCase
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import VacancyFactory
from tests.fixtures.domain_graph import build_vacancy_with_graph

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return UpdateVacancyStatusUseCase(mock_uow)


async def test_update_vacancy_status_use_case_changes_status_on_allowed_transition(
    use_case: UpdateVacancyStatusUseCase, mock_uow
) -> None:
    vacancy, _, _, _, _ = build_vacancy_with_graph()
    vacancy.status = VacancyStatus.DRAFT
    vacancy.error_message = "old error"
    mock_uow.vacancies.get.return_value = vacancy

    result = await use_case.execute(
        vacancy.id, VacancyStatusUpdateDTO(status=VacancyStatus.READY)
    )

    assert result.status == VacancyStatus.READY
    assert vacancy.error_message is None
    assert len(vacancy.category_nodes) > 0
    assert len(vacancy.competency_nodes) > 0
    assert len(vacancy.sub_competency_nodes) > 0
    mock_uow.vacancies.get.assert_any_await(
        vacancy.id,
        include={VacancyInclude.NORMALIZED_GRAPH},
    )
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_update_vacancy_status_use_case_rejects_invalid_transition(
    use_case: UpdateVacancyStatusUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.READY})
    mock_uow.vacancies.get.return_value = vacancy

    with pytest.raises(ValidationError, match="Invalid status transition"):
        await use_case.execute(
            vacancy.id, VacancyStatusUpdateDTO(status=VacancyStatus.PENDING)
        )


async def test_update_vacancy_status_use_case_raises_when_vacancy_not_found(
    use_case: UpdateVacancyStatusUseCase, mock_uow
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(
            uuid4(), VacancyStatusUpdateDTO(status=VacancyStatus.DRAFT)
        )
