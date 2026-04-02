from __future__ import annotations

from collections.abc import Collection, Sequence
from datetime import datetime
from enum import StrEnum, auto
from typing import Any, Protocol, TypeVar
from uuid import UUID

from competency_system.application.dtos.webhooks import RankingSnapshot, WebhookEvent
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
from competency_system.domain.value_objects.enums import VacancyStatus


class CategoryInclude(StrEnum):
    COMPETENCIES = auto()
    SUB_COMPETENCIES = auto()


class CompetencyInclude(StrEnum):
    CATEGORY = auto()
    SUB_COMPETENCIES = auto()


class VacancyInclude(StrEnum):
    NORMALIZED_GRAPH = auto()


class CandidateInclude(StrEnum):
    ACHIEVEMENTS = auto()
    TEST_RESULTS = auto()
    VACANCY = auto()
    VACANCY_SUBCOMPETENCIES = auto()


class TaskInclude(StrEnum):
    SUB_COMPETENCY_MAPPINGS = auto()


class TestResultInclude(StrEnum):
    QUESTION_ANSWERS = auto()
    LLM_ASSESSMENT = auto()
    TASK = auto()
    CANDIDATE = auto()


class VacancyGraphSuggestionInclude(StrEnum):
    VACANCY = auto()
    PARENT_CATEGORY = auto()
    PARENT_COMPETENCY = auto()


EntityT = TypeVar("EntityT")


class Repository(Protocol[EntityT]):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: Any | None = None,
    ) -> EntityT | None: ...

    async def get_list(
        self,
        *,
        include: Any | None = None,
    ) -> Sequence[EntityT]: ...

    async def add(self, entity: EntityT) -> None: ...

    async def delete(self, entity_id: UUID) -> None: ...


class CategoryRepository(Repository[Category], Protocol):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[CategoryInclude] | None = None,
    ) -> Category | None: ...

    async def get_list(
        self,
        *,
        include: Collection[CategoryInclude] | None = None,
    ) -> Sequence[Category]: ...


class CompetencyRepository(Repository[Competency], Protocol):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[CompetencyInclude] | None = None,
    ) -> Competency | None: ...

    async def get_list(
        self,
        *,
        include: Collection[CompetencyInclude] | None = None,
    ) -> Sequence[Competency]: ...


class SubCompetencyRepository(Repository[SubCompetency], Protocol):
    pass


class VacancyRepository(Repository[Vacancy], Protocol):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[VacancyInclude] | None = None,
    ) -> Vacancy | None: ...

    async def get_list(
        self,
        *,
        include: Collection[VacancyInclude] | None = None,
    ) -> Sequence[Vacancy]: ...

    async def list_by_statuses(
        self,
        statuses: set[VacancyStatus] | None = None,
        *,
        include: Collection[VacancyInclude] | None = None,
    ) -> Sequence[Vacancy]: ...


class CandidateRepository(Repository[Candidate], Protocol):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[CandidateInclude] | None = None,
    ) -> Candidate | None: ...

    async def get_list(
        self,
        *,
        include: Collection[CandidateInclude] | None = None,
    ) -> Sequence[Candidate]: ...

    async def get_by_external_id(
        self,
        external_id: str,
        *,
        include: Collection[CandidateInclude] | None = None,
    ) -> Candidate | None: ...

    async def list_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: Collection[CandidateInclude] | None = None,
    ) -> Sequence[Candidate]: ...


class TaskRepository(Repository[Task], Protocol):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[TaskInclude] | None = None,
    ) -> Task | None: ...

    async def get_list(
        self,
        *,
        include: Collection[TaskInclude] | None = None,
    ) -> Sequence[Task]: ...

    async def get_by_external_id(
        self,
        external_id: str,
        *,
        include: Collection[TaskInclude] | None = None,
    ) -> Task | None: ...


class TestResultRepository(Repository[TestResult], Protocol):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[TestResultInclude] | None = None,
    ) -> TestResult | None: ...

    async def get_list(
        self,
        *,
        include: Collection[TestResultInclude] | None = None,
    ) -> Sequence[TestResult]: ...


class VacancySuggestionRepository(Repository[VacancyGraphSuggestion], Protocol):
    async def list_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: Collection[VacancyGraphSuggestionInclude] | None = None,
    ) -> Sequence[VacancyGraphSuggestion]: ...


class UserRepository(Repository[User], Protocol):
    async def get(
        self,
        entity_id: UUID,
        *,
        include: None = None,
    ) -> User | None: ...

    async def get_list(
        self,
        *,
        include: None = None,
    ) -> Sequence[User]: ...

    async def get_by_email(
        self,
        email: str,
        *,
        include: None = None,
    ) -> User | None: ...


class WebhookEventRepository(Repository[WebhookEvent], Protocol):
    async def get_by_event_id(
        self, event_id: str, *, include: object | None = None
    ) -> WebhookEvent | None: ...


class RankingSnapshotRepository(Repository[RankingSnapshot], Protocol):
    async def get_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: object | None = None,
    ) -> RankingSnapshot | None: ...


class RefreshTokenRepository(Repository[RefreshToken], Protocol):
    async def add_token(
        self,
        *,
        jti: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None: ...

    async def get_by_jti(
        self,
        jti: UUID,
        *,
        include: None = None,
    ) -> RefreshToken | None: ...

    async def revoke(self, jti: UUID) -> None: ...
