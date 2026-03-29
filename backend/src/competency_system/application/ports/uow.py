from __future__ import annotations

from types import TracebackType
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import (
    CandidateRepository,
    CategoryRepository,
    CompetencyRepository,
    RankingSnapshotRepository,
    RefreshTokenRepository,
    SubCompetencyRepository,
    TaskRepository,
    TestResultRepository,
    UserRepository,
    VacancyRepository,
    VacancySuggestionRepository,
    WebhookEventRepository,
)


class UnitOfWork(Protocol):
    session: AsyncSession
    categories: CategoryRepository
    competencies: CompetencyRepository
    sub_competencies: SubCompetencyRepository
    vacancies: VacancyRepository
    candidates: CandidateRepository
    tasks: TaskRepository
    test_results: TestResultRepository
    vacancy_suggestions: VacancySuggestionRepository
    webhook_events: WebhookEventRepository
    ranking_snapshots: RankingSnapshotRepository
    users: UserRepository
    refresh_tokens: RefreshTokenRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None: ...
