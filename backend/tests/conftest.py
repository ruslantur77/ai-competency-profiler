from __future__ import annotations

import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from unittest.mock import AsyncMock

from competency_system.infrastructure.settings import get_settings


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("integration-db")
    group.addoption(
        "--test-db-url",
        action="store",
        default=None,
        help=(
            "PostgreSQL URL for integration tests. "
            "Example: postgresql://user:pass@127.0.0.1:5432/test_db"
        ),
    )
    group.addoption("--test-db-host", action="store", default=None)
    group.addoption("--test-db-port", action="store", default=None)
    group.addoption("--test-db-name", action="store", default=None)
    group.addoption("--test-db-user", action="store", default=None)
    group.addoption("--test-db-pass", action="store", default=None)


@pytest.fixture(autouse=True)
def test_environment_guard() -> None:
    tracked_keys = (
        "BOOTSTRAP_ADMIN_EMAIL",
        "BOOTSTRAP_ADMIN_PASSWORD",
        "TESTING_SYSTEM_WEBHOOK_SECRET",
    )
    previous = {key: os.environ.get(key) for key in tracked_keys}

    os.environ["BOOTSTRAP_ADMIN_EMAIL"] = ""
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = ""
    os.environ["TESTING_SYSTEM_WEBHOOK_SECRET"] = ""
    get_settings.cache_clear()
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


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
        categories=_repo_mock("get", "list", "add", "delete"),
        competencies=_repo_mock("get", "list", "add", "delete"),
        sub_competencies=_repo_mock("get", "list", "add", "delete"),
        vacancies=_repo_mock("get", "list", "add", "delete", "list_by_statuses"),
        candidates=_repo_mock("get", "list", "add", "delete", "get_by_external_id", "list_by_vacancy"),
        tasks=_repo_mock("get", "list", "add", "delete", "get_by_external_id"),
        test_results=_repo_mock("get", "list", "add", "delete"),
        vacancy_suggestions=_repo_mock("get", "list", "add", "delete", "list_by_vacancy"),
        webhook_events=_repo_mock("get", "list", "add", "delete", "get_by_event_id"),
        ranking_snapshots=_repo_mock("get", "list", "add", "delete", "get_by_vacancy"),
        users=_repo_mock("get", "list", "add", "delete", "get_by_email"),
        refresh_tokens=_repo_mock("get", "list", "add", "delete", "add_token", "get_by_jti", "revoke"),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        flush=AsyncMock(),
    )
