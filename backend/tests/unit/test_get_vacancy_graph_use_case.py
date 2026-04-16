from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.vacancy import GetVacancyGraphUseCase
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return GetVacancyGraphUseCase(mock_uow)


async def test_get_vacancy_graph_use_case_returns_vacancy(
    use_case: GetVacancyGraphUseCase, mock_uow
) -> None:
    vacancy = VacancyFactory().make({"name": "Backend Engineer"})
    mock_uow.vacancies.get.return_value = vacancy

    result = await use_case.execute(vacancy.id)

    assert result.id == vacancy.id
    assert result.name == "Backend Engineer"


async def test_get_vacancy_graph_use_case_raises_when_vacancy_not_found(
    use_case: GetVacancyGraphUseCase, mock_uow
) -> None:
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(uuid4())
