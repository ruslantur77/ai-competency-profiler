from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest


def _repo_mock(*method_names: str) -> SimpleNamespace:
    return SimpleNamespace(**{name: AsyncMock() for name in method_names})


@dataclass
class MockUnitOfWork:
    categories: Any
    competencies: Any
    sub_competencies: Any
    vacancies: Any
    candidates: Any
    tasks: Any
    test_results: Any
    vacancy_suggestions: Any
    webhook_events: Any
    ranking_snapshots: Any
    users: Any
    refresh_tokens: Any
    commit: AsyncMock
    rollback: AsyncMock
    flush: AsyncMock

    async def __aenter__(self) -> MockUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


@pytest.fixture()
def mock_uow() -> MockUnitOfWork:
    return MockUnitOfWork(
        categories=_repo_mock("get", "get_list", "add", "delete", "list"),
        competencies=_repo_mock("get", "get_list", "add", "delete", "list"),
        sub_competencies=_repo_mock("get", "get_list", "add", "delete", "list"),
        vacancies=_repo_mock(
            "get",
            "get_list",
            "add",
            "delete",
            "list_by_statuses",
            "list",
        ),
        candidates=_repo_mock(
            "get",
            "get_list",
            "add",
            "delete",
            "get_by_external_id",
            "list_by_vacancy",
            "list",
        ),
        tasks=_repo_mock(
            "get",
            "get_list",
            "add",
            "delete",
            "get_by_external_id",
            "list",
        ),
        test_results=_repo_mock("get", "get_list", "add", "delete", "list"),
        vacancy_suggestions=_repo_mock(
            "get",
            "get_list",
            "add",
            "delete",
            "list_by_vacancy",
            "list",
        ),
        webhook_events=_repo_mock(
            "get", "get_list", "add", "delete", "get_by_event_id", "list"
        ),
        ranking_snapshots=_repo_mock(
            "get", "get_list", "add", "delete", "get_by_vacancy", "list"
        ),
        users=_repo_mock("get", "get_list", "add", "delete", "get_by_email", "list"),
        refresh_tokens=_repo_mock(
            "get",
            "get_list",
            "add",
            "delete",
            "add_token",
            "get_by_jti",
            "revoke",
            "list",
        ),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        flush=AsyncMock(),
    )
