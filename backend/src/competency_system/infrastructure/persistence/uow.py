from __future__ import annotations

from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from competency_system.infrastructure.persistence.repositories import (
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


class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession
        self.categories: CategoryRepository
        self.competencies: CompetencyRepository
        self.sub_competencies: SubCompetencyRepository
        self.vacancies: VacancyRepository
        self.candidates: CandidateRepository
        self.tasks: TaskRepository
        self.test_results: TestResultRepository
        self.vacancy_suggestions: VacancySuggestionRepository
        self.users: UserRepository
        self.refresh_tokens: RefreshTokenRepository

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        self.categories = CategoryRepository(self.session)
        self.competencies = CompetencyRepository(self.session)
        self.sub_competencies = SubCompetencyRepository(self.session)
        self.vacancies = VacancyRepository(self.session)
        self.candidates = CandidateRepository(self.session)
        self.tasks = TaskRepository(self.session)
        self.test_results = TestResultRepository(self.session)
        self.vacancy_suggestions = VacancySuggestionRepository(self.session)
        self.users = UserRepository(self.session)
        self.refresh_tokens = RefreshTokenRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()
