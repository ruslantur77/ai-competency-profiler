from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from competency_system.application.dtos.vacancy import (
    VacancyGraphUpdateDTO,
    VacancyUpdateDTO,
)
from competency_system.application.errors import ConflictError, NotFoundError
from competency_system.application.use_cases.vacancy import (
    DeleteVacancyUseCase,
    HardDeleteVacancyUseCase,
    RestoreVacancyUseCase,
    SaveVacancyGraphUseCase,
    UpdateVacancyUseCase,
)
from tests.factories.domain import VacancyFactory

pytestmark = pytest.mark.unit


async def test_update_vacancy_use_case_updates_name(mock_uow) -> None:
    use_case = UpdateVacancyUseCase(mock_uow)
    vacancy = VacancyFactory().make({"name": "Old"})
    mock_uow.vacancies.get.return_value = vacancy

    result = await use_case.execute(vacancy.id, VacancyUpdateDTO(name="  New Name  "))

    assert result.name == "New Name"
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.commit.assert_awaited_once()


async def test_update_vacancy_use_case_raises_conflict_for_deleted(mock_uow) -> None:
    use_case = UpdateVacancyUseCase(mock_uow)
    vacancy_id = uuid4()
    deleted = VacancyFactory().make({"id": vacancy_id, "deleted_at": datetime.now(UTC)})
    mock_uow.vacancies.get.side_effect = [None, deleted]

    with pytest.raises(ConflictError):
        await use_case.execute(vacancy_id, VacancyUpdateDTO(name="New"))


async def test_soft_delete_vacancy_use_case_commits(mock_uow) -> None:
    use_case = DeleteVacancyUseCase(mock_uow)
    vacancy = VacancyFactory().make()
    mock_uow.vacancies.soft_delete.return_value = vacancy

    await use_case.execute(vacancy.id)

    mock_uow.vacancies.soft_delete.assert_awaited_once_with(vacancy.id)
    mock_uow.commit.assert_awaited_once()


async def test_restore_vacancy_use_case_returns_vacancy(mock_uow) -> None:
    use_case = RestoreVacancyUseCase(mock_uow)
    vacancy = VacancyFactory().make()
    mock_uow.vacancies.restore.return_value = vacancy

    result = await use_case.execute(vacancy.id)

    assert result.id == vacancy.id
    mock_uow.commit.assert_awaited_once()


async def test_hard_delete_vacancy_use_case_raises_when_not_found(mock_uow) -> None:
    use_case = HardDeleteVacancyUseCase(mock_uow)
    vacancy_id = uuid4()
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError):
        await use_case.execute(vacancy_id)


async def test_save_vacancy_graph_use_case_raises_conflict_for_deleted(
    mock_uow,
) -> None:
    use_case = SaveVacancyGraphUseCase(mock_uow)
    vacancy_id = uuid4()
    deleted = VacancyFactory().make({"id": vacancy_id, "deleted_at": datetime.now(UTC)})
    mock_uow.vacancies.get.side_effect = [None, deleted]

    with pytest.raises(ConflictError):
        await use_case.execute(vacancy_id, graph=VacancyGraphUpdateDTO(categories=[]))
