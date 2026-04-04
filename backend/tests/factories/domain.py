from __future__ import annotations

from datetime import UTC, datetime
from typing import NotRequired, TypedDict
from uuid import UUID, uuid4

from competency_system.domain.entities import Candidate, Task, TestResult, User, Vacancy
from competency_system.domain.value_objects.enums import (
    AssessmentStatus,
    TaskMappingStatus,
    TaskType,
    UserRole,
    VacancyStatus,
)
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    TaskOrm,
    TestResultOrm,
    UserOrm,
    VacancyOrm,
)
from tests.factories.factory import AbstractFactory


class UserFields(TypedDict):
    id: NotRequired[UUID]
    email: NotRequired[str]
    role: NotRequired[UserRole]
    is_active: NotRequired[bool]
    hashed_password: NotRequired[str]


class UserFactory(AbstractFactory[UserFields, User, UserOrm]):
    def make(self, fields: UserFields | None = None) -> User:
        data = fields or {}
        return User(
            id=data.get("id", uuid4()),
            email=data.get("email", "hr@example.com"),
            role=data.get("role", UserRole.HR),
            is_active=data.get("is_active", True),
            hashed_password=data.get("hashed_password", "hashed-password"),
        )

    def make_orm(self, fields: UserFields | None = None) -> UserOrm:
        return UserOrm.from_entity(self.make(fields))


class VacancyFields(TypedDict):
    id: NotRequired[UUID]
    name: NotRequired[str]
    description: NotRequired[str]
    status: NotRequired[VacancyStatus]
    error_message: NotRequired[str | None]


class VacancyFactory(AbstractFactory[VacancyFields, Vacancy, VacancyOrm]):
    def make(self, fields: VacancyFields | None = None) -> Vacancy:
        data = fields or {}
        return Vacancy(
            id=data.get("id", uuid4()),
            name=data.get("name", "Backend Engineer"),
            description=data.get("description", "Build APIs"),
            status=data.get("status", VacancyStatus.DRAFT),
            error_message=data.get("error_message", None),
        )

    def make_orm(self, fields: VacancyFields | None = None) -> VacancyOrm:
        return VacancyOrm.from_entity(self.make(fields))


class CandidateFields(TypedDict):
    id: NotRequired[UUID]
    external_id: NotRequired[str]
    vacancy_id: NotRequired[UUID]
    status: NotRequired[AssessmentStatus]
    last_assessment_at: NotRequired[datetime | None]


class CandidateFactory(AbstractFactory[CandidateFields, Candidate, CandidateOrm]):
    def make(self, fields: CandidateFields | None = None) -> Candidate:
        data = fields or {}
        return Candidate(
            id=data.get("id", uuid4()),
            external_id=data.get("external_id", "candidate-1"),
            vacancy_id=data.get("vacancy_id", uuid4()),
            status=data.get("status", AssessmentStatus.PENDING),
            last_assessment_at=data.get("last_assessment_at", None),
        )

    def make_orm(self, fields: CandidateFields | None = None) -> CandidateOrm:
        return CandidateOrm.from_entity(self.make(fields))


class TaskFields(TypedDict):
    id: NotRequired[UUID]
    external_id: NotRequired[str]
    title: NotRequired[str]
    description: NotRequired[str]
    type: NotRequired[TaskType]
    mapping_validated: NotRequired[bool]
    mapping_status: NotRequired[TaskMappingStatus]
    mapping_error_message: NotRequired[str | None]


class TaskFactory(AbstractFactory[TaskFields, Task, TaskOrm]):
    def make(self, fields: TaskFields | None = None) -> Task:
        data = fields or {}
        return Task(
            id=data.get("id", uuid4()),
            external_id=data.get("external_id", "task-1"),
            title=data.get("title", "Task title"),
            description=data.get("description", "Task description"),
            type=data.get("type", TaskType.CODE),
            mapping_validated=data.get("mapping_validated", False),
            mapping_status=data.get("mapping_status", TaskMappingStatus.PENDING),
            mapping_error_message=data.get("mapping_error_message", None),
        )

    def make_orm(self, fields: TaskFields | None = None) -> TaskOrm:
        return TaskOrm.from_entity(self.make(fields))


class TestResultFields(TypedDict):
    id: NotRequired[UUID]
    candidate_id: NotRequired[UUID]
    task_id: NotRequired[UUID]
    passed: NotRequired[bool]
    score: NotRequired[float]
    attempts: NotRequired[int]
    code_submitted: NotRequired[str | None]


class TestResultFactory(AbstractFactory[TestResultFields, TestResult, TestResultOrm]):
    def make(self, fields: TestResultFields | None = None) -> TestResult:
        data = fields or {}
        return TestResult(
            id=data.get("id", uuid4()),
            candidate_id=data.get("candidate_id", uuid4()),
            task_id=data.get("task_id", uuid4()),
            passed=data.get("passed", False),
            score=data.get("score", 0.0),
            attempts=data.get("attempts", 1),
            code_submitted=data.get("code_submitted", None),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def make_orm(self, fields: TestResultFields | None = None) -> TestResultOrm:
        return TestResultOrm.from_entity(self.make(fields))
