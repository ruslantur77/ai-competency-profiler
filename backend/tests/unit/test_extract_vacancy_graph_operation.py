# ruff: noqa: E501
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from competency_system.application.use_cases.vacancy import (
    ExtractVacancyGraphOperation,
)
from competency_system.domain.value_objects.enums import VacancyStatus
from tests.factories import VacancyFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def operation(mock_uow, llm_gateway_mock):
    return ExtractVacancyGraphOperation(mock_uow, llm_gateway_mock)


async def test_extract_vacancy_graph_operation_sets_draft_status_on_success(
    operation: ExtractVacancyGraphOperation, mock_uow
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.PENDING})
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.categories.get_list.return_value = []
    suggestion = type("Suggestion", (), {"vacancy_id": None})()
    operation._map = AsyncMock(
        return_value=type(
            "_Graph",
            (),
            {
                "category_nodes": [],
                "competency_nodes": [],
                "sub_competency_nodes": [],
                "suggestions": [suggestion],
            },
        )()
    )

    await operation.run(vacancy.id)

    assert vacancy.status == VacancyStatus.DRAFT
    assert suggestion.vacancy_id == vacancy.id
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)
    mock_uow.vacancy_suggestions.add.assert_awaited_once_with(suggestion)


async def test_extract_vacancy_graph_operation_sets_failed_status_on_error(
    operation: ExtractVacancyGraphOperation, mock_uow
) -> None:
    vacancy = VacancyFactory().make({"status": VacancyStatus.PENDING})
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.categories.get_list.return_value = []
    operation._map = AsyncMock(side_effect=RuntimeError("llm failed"))

    await operation.run(vacancy.id)

    assert vacancy.status == VacancyStatus.FAILED
    assert vacancy.error_message == "llm failed"
    mock_uow.vacancies.add.assert_awaited_once_with(vacancy)


async def test_extract_vacancy_graph_operation_returns_when_vacancy_missing(
    operation: ExtractVacancyGraphOperation, mock_uow
) -> None:
    mock_uow.vacancies.get.return_value = None

    await operation.run(VacancyFactory().make().id)

    mock_uow.vacancies.add.assert_not_awaited()


async def test_extract_vacancy_graph_operation_reraises_when_loading_fails_before_vacancy(
    operation: ExtractVacancyGraphOperation, mock_uow
) -> None:
    mock_uow.vacancies.get.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError, match="db error"):
        await operation.run(VacancyFactory().make().id)
