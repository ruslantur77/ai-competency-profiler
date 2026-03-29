from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, TypeVar
from uuid import UUID

from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    RefreshToken,
    SubCompetency,
    Task,
    TestResult,
    User,
    Vacancy,
    VacancyGraphSuggestion,
)

EntityT = TypeVar("EntityT")


class Repository(Protocol[EntityT]):
    async def get(self, entity_id: UUID) -> EntityT | None: ...

    async def list(self) -> Sequence[EntityT]: ...

    async def add(self, entity: EntityT) -> None: ...

    async def delete(self, entity_id: UUID) -> None: ...


class CategoryRepository(Repository[Category], Protocol):
    pass


class CompetencyRepository(Repository[Competency], Protocol):
    pass


class SubCompetencyRepository(Repository[SubCompetency], Protocol):
    pass


class VacancyRepository(Repository[Vacancy], Protocol):
    pass


class CandidateRepository(Repository[Candidate], Protocol):
    async def get_by_external_id(self, external_id: str) -> Candidate | None: ...


class TaskRepository(Repository[Task], Protocol):
    async def get_by_external_id(self, external_id: str) -> Task | None: ...


class TestResultRepository(Repository[TestResult], Protocol):
    pass


class VacancySuggestionRepository(Repository[VacancyGraphSuggestion], Protocol):
    async def list_by_vacancy(self, vacancy_id: UUID) -> Sequence[VacancyGraphSuggestion]: ...


class UserRepository(Repository[User], Protocol):
    async def get_by_email(self, email: str) -> User | None: ...


class RefreshTokenRepository(Repository[RefreshToken], Protocol):
    async def add_token(
        self,
        *,
        jti: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None: ...

    async def get_by_jti(self, jti: UUID) -> RefreshToken | None: ...

    async def revoke(self, jti: UUID) -> None: ...
