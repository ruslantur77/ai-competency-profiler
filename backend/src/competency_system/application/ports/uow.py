from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import (
    CandidateRepository,
    CategoryRepository,
    CompetencyRepository,
    RefreshTokenRepository,
    SubCompetencyRepository,
    TaskRepository,
    TestResultRepository,
    UserRepository,
    VacancyRepository,
    VacancySuggestionRepository,
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
    users: UserRepository
    refresh_tokens: RefreshTokenRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None: ...
