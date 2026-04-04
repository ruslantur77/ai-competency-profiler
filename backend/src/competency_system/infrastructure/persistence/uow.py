from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from competency_system.application.ports.repositories import (
    CandidateRepository as CandidateRepositoryPort,
)
from competency_system.application.ports.repositories import (
    CategoryRepository as CategoryRepositoryPort,
)
from competency_system.application.ports.repositories import (
    CompetencyRepository as CompetencyRepositoryPort,
)
from competency_system.application.ports.repositories import (
    RankingSnapshotRepository as RankingSnapshotRepositoryPort,
)
from competency_system.application.ports.repositories import (
    RefreshTokenRepository as RefreshTokenRepositoryPort,
)
from competency_system.application.ports.repositories import (
    SubCompetencyRepository as SubCompetencyRepositoryPort,
)
from competency_system.application.ports.repositories import (
    TaskRepository as TaskRepositoryPort,
)
from competency_system.application.ports.repositories import (
    TestResultRepository as TestResultRepositoryPort,
)
from competency_system.application.ports.repositories import (
    UserRepository as UserRepositoryPort,
)
from competency_system.application.ports.repositories import (
    VacancyRepository as VacancyRepositoryPort,
)
from competency_system.application.ports.repositories import (
    VacancySuggestionRepository as VacancySuggestionRepositoryPort,
)
from competency_system.application.ports.repositories import (
    WebhookEventRepository as WebhookEventRepositoryPort,
)
from competency_system.application.ports.uow import UnitOfWork
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


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession
        self.categories: CategoryRepositoryPort
        self.competencies: CompetencyRepositoryPort
        self.sub_competencies: SubCompetencyRepositoryPort
        self.vacancies: VacancyRepositoryPort
        self.candidates: CandidateRepositoryPort
        self.tasks: TaskRepositoryPort
        self.test_results: TestResultRepositoryPort
        self.vacancy_suggestions: VacancySuggestionRepositoryPort
        self.webhook_events: WebhookEventRepositoryPort
        self.ranking_snapshots: RankingSnapshotRepositoryPort
        self.users: UserRepositoryPort
        self.refresh_tokens: RefreshTokenRepositoryPort

    async def __aenter__(self) -> UnitOfWork:
        self.session = self._session_factory()
        self.categories = CategoryRepository(self.session)
        self.competencies = CompetencyRepository(self.session)
        self.sub_competencies = SubCompetencyRepository(self.session)
        self.vacancies = VacancyRepository(self.session)
        self.candidates = CandidateRepository(self.session)
        self.tasks = TaskRepository(self.session)
        self.test_results = _TestResultRepository(self.session)
        self.vacancy_suggestions = VacancySuggestionRepository(self.session)
        self.webhook_events = WebhookEventRepository(self.session)
        self.ranking_snapshots = RankingSnapshotRepository(self.session)
        self.users = UserRepository(self.session)
        self.refresh_tokens = RefreshTokenRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()
