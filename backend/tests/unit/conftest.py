from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from competency_system.infrastructure.persistence.repositories import (
    CandidateRepository,
    CategoryRepository,
    CompetencyRepository,
    RankingSnapshotRepository,
    RefreshTokenRepository,
    SubCompetencyRepository,
    TaskRepository,
    UserRepository,
    VacancyRepository,
    VacancySuggestionRepository,
    WebhookEventRepository,
    _TestResultRepository,
)


def _make_async_aware_autospec(cls: type[Any]) -> Any:
    mock = create_autospec(cls, instance=True, spec_set=True)
    for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
        if inspect.iscoroutinefunction(member):
            setattr(mock, name, AsyncMock())
    return mock


@pytest.fixture
def repos_mock_factory() -> Any:
    return _make_async_aware_autospec


@pytest.fixture
def category_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(CategoryRepository)


@pytest.fixture
def competency_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(CompetencyRepository)


@pytest.fixture
def sub_competency_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(SubCompetencyRepository)


@pytest.fixture
def vacancy_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(VacancyRepository)


@pytest.fixture
def candidate_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(CandidateRepository)


@pytest.fixture
def task_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(TaskRepository)


@pytest.fixture
def test_result_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(_TestResultRepository)


@pytest.fixture
def vacancy_suggestion_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(VacancySuggestionRepository)


@pytest.fixture
def webhook_event_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(WebhookEventRepository)


@pytest.fixture
def ranking_snapshot_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(RankingSnapshotRepository)


@pytest.fixture
def user_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(UserRepository)


@pytest.fixture
def refresh_token_repo_mock(repos_mock_factory: Any) -> Any:
    return repos_mock_factory(RefreshTokenRepository)


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
    session: Any

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


@pytest.fixture
def mock_uow(
    category_repo_mock: Any,
    competency_repo_mock: Any,
    sub_competency_repo_mock: Any,
    vacancy_repo_mock: Any,
    candidate_repo_mock: Any,
    task_repo_mock: Any,
    test_result_repo_mock: Any,
    vacancy_suggestion_repo_mock: Any,
    webhook_event_repo_mock: Any,
    ranking_snapshot_repo_mock: Any,
    user_repo_mock: Any,
    refresh_token_repo_mock: Any,
) -> MockUnitOfWork:
    return MockUnitOfWork(
        categories=category_repo_mock,
        competencies=competency_repo_mock,
        sub_competencies=sub_competency_repo_mock,
        vacancies=vacancy_repo_mock,
        candidates=candidate_repo_mock,
        tasks=task_repo_mock,
        test_results=test_result_repo_mock,
        vacancy_suggestions=vacancy_suggestion_repo_mock,
        webhook_events=webhook_event_repo_mock,
        ranking_snapshots=ranking_snapshot_repo_mock,
        users=user_repo_mock,
        refresh_tokens=refresh_token_repo_mock,
        commit=AsyncMock(),
        rollback=AsyncMock(),
        flush=AsyncMock(),
        session=MagicMock(name="uow_session"),
    )
