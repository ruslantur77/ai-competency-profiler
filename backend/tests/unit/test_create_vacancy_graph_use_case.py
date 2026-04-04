from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import VacancyCreateDTO
from competency_system.application.use_cases.vacancy import CreateVacancyGraphUseCase
from competency_system.domain.value_objects.enums import VacancyStatus

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow, job_queue_mock):
    return CreateVacancyGraphUseCase(mock_uow, job_queue_mock)


@pytest.fixture
def create_command() -> VacancyCreateDTO:
    return VacancyCreateDTO(
        name="Python Engineer", description="Build backend services"
    )


async def test_create_vacancy_graph_use_case_persists_vacancy_and_enqueues(
    use_case: CreateVacancyGraphUseCase,
    mock_uow,
    job_queue_mock,
    create_command: VacancyCreateDTO,
) -> None:
    job_queue_mock.enqueue.return_value = uuid4()

    result = await use_case.execute(create_command)

    assert result.name == create_command.name
    assert result.status == VacancyStatus.PENDING
    mock_uow.vacancies.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()
    job_queue_mock.enqueue.assert_awaited_once()


async def test_create_vacancy_graph_use_case_propagates_enqueue_errors(
    use_case: CreateVacancyGraphUseCase,
    mock_uow,
    job_queue_mock,
    create_command: VacancyCreateDTO,
) -> None:
    job_queue_mock.enqueue.side_effect = RuntimeError("queue unavailable")

    with pytest.raises(RuntimeError, match="queue unavailable"):
        await use_case.execute(create_command)
