from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import NotRequired, TypedDict
from uuid import UUID, uuid4

from competency_system.application.dtos.webhooks import (
    RankingSnapshot,
    RankingSnapshotPayload,
    WebhookEvent,
    WebhookEventPayload,
)
from competency_system.domain.entities import (
    Candidate,
    CandidateSubCompetencyAchievement,
    Category,
    Competency,
    RefreshToken,
    SubCompetency,
    Task,
    TaskSubCompetencyMapping,
    TestResult,
    TestResultLLMAssessment,
    TestResultLLMFeedbackItem,
    TestResultQuestionAnswer,
    User,
    Vacancy,
    VacancyCategoryNode,
    VacancyCompetencyNode,
    VacancyGraphSuggestion,
    VacancySubCompetencyNode,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    AssessmentStatus,
    LLMFeedbackType,
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    TaskMappingStatus,
    TaskType,
    UserRole,
    VacancyStatus,
)
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CategoryOrm,
    CompetencyOrm,
    RankingSnapshotOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    TestResultOrm,
    UserOrm,
    VacancyCategoryNodeOrm,
    VacancyCompetencyNodeOrm,
    VacancyOrm,
    VacancySubCompetencyNodeOrm,
    VacancySuggestionOrm,
    WebhookEventOrm,
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


class RefreshTokenFields(TypedDict):
    jti: NotRequired[UUID]
    user_id: NotRequired[UUID]
    token_hash: NotRequired[str]
    expires_at: NotRequired[datetime]
    revoked_at: NotRequired[datetime | None]


class RefreshTokenFactory(AbstractFactory[RefreshTokenFields, RefreshToken, RefreshTokenOrm]):
    def make(self, fields: RefreshTokenFields | None = None) -> RefreshToken:
        data = fields or {}
        return RefreshToken(
            jti=data.get("jti", uuid4()),
            user_id=data.get("user_id", uuid4()),
            token_hash=data.get("token_hash", "token-hash"),
            expires_at=data.get("expires_at", datetime.now(UTC) + timedelta(days=7)),
            revoked_at=data.get("revoked_at", None),
        )

    def make_orm(self, fields: RefreshTokenFields | None = None) -> RefreshTokenOrm:
        return RefreshTokenOrm.from_entity(self.make(fields))


class CategoryFields(TypedDict):
    id: NotRequired[UUID]
    name: NotRequired[str]
    description: NotRequired[str]
    emoji: NotRequired[str]
    competencies: NotRequired[list[Competency]]


class CategoryFactory(AbstractFactory[CategoryFields, Category, CategoryOrm]):
    def make(self, fields: CategoryFields | None = None) -> Category:
        data = fields or {}
        return Category(
            id=data.get("id", uuid4()),
            name=data.get("name", "Engineering"),
            description=data.get("description", "Engineering skills"),
            emoji=data.get("emoji", "🛠"),
            competencies=data.get("competencies", []),
        )

    def make_orm(self, fields: CategoryFields | None = None) -> CategoryOrm:
        return CategoryOrm.from_entity(self.make(fields))


class CompetencyFields(TypedDict):
    id: NotRequired[UUID]
    category_id: NotRequired[UUID]
    name: NotRequired[str]
    description: NotRequired[str]
    sub_competencies: NotRequired[list[SubCompetency]]
    category: NotRequired[Category | None]


class CompetencyFactory(AbstractFactory[CompetencyFields, Competency, CompetencyOrm]):
    def make(self, fields: CompetencyFields | None = None) -> Competency:
        data = fields or {}
        return Competency(
            id=data.get("id", uuid4()),
            category_id=data.get("category_id", uuid4()),
            name=data.get("name", "Backend"),
            description=data.get("description", "Core backend"),
            sub_competencies=data.get("sub_competencies", []),
            category=data.get("category", None),
        )

    def make_orm(self, fields: CompetencyFields | None = None) -> CompetencyOrm:
        return CompetencyOrm.from_entity(self.make(fields))


class SubCompetencyFields(TypedDict):
    id: NotRequired[UUID]
    competency_id: NotRequired[UUID]
    name: NotRequired[str]
    description: NotRequired[str]
    weight: NotRequired[float]
    target_level: NotRequired[CompetencyLevel]
    competency: NotRequired[Competency | None]


class SubCompetencyFactory(AbstractFactory[SubCompetencyFields, SubCompetency, SubCompetencyOrm]):
    def make(self, fields: SubCompetencyFields | None = None) -> SubCompetency:
        data = fields or {}
        return SubCompetency(
            id=data.get("id", uuid4()),
            competency_id=data.get("competency_id", uuid4()),
            name=data.get("name", "REST"),
            description=data.get("description", "REST APIs"),
            weight=data.get("weight", 1.0),
            target_level=data.get("target_level", CompetencyLevel.EXPERT),
            competency=data.get("competency", None),
        )

    def make_orm(self, fields: SubCompetencyFields | None = None) -> SubCompetencyOrm:
        return SubCompetencyOrm.from_entity(self.make(fields))


class VacancyFields(TypedDict):
    id: NotRequired[UUID]
    name: NotRequired[str]
    description: NotRequired[str]
    status: NotRequired[VacancyStatus]
    error_message: NotRequired[str | None]
    category_nodes: NotRequired[list[VacancyCategoryNode]]
    competency_nodes: NotRequired[list[VacancyCompetencyNode]]
    sub_competency_nodes: NotRequired[list[VacancySubCompetencyNode]]
    suggestions: NotRequired[list[VacancyGraphSuggestion]]


class VacancyFactory(AbstractFactory[VacancyFields, Vacancy, VacancyOrm]):
    def make(self, fields: VacancyFields | None = None) -> Vacancy:
        data = fields or {}
        return Vacancy(
            id=data.get("id", uuid4()),
            name=data.get("name", "Backend Engineer"),
            description=data.get("description", "Build APIs"),
            status=data.get("status", VacancyStatus.DRAFT),
            error_message=data.get("error_message", None),
            category_nodes=data.get("category_nodes", []),
            competency_nodes=data.get("competency_nodes", []),
            sub_competency_nodes=data.get("sub_competency_nodes", []),
            suggestions=data.get("suggestions", []),
        )

    def make_orm(self, fields: VacancyFields | None = None) -> VacancyOrm:
        return VacancyOrm.from_entity(self.make(fields))


class VacancyCategoryNodeFields(TypedDict):
    id: NotRequired[UUID]
    vacancy_id: NotRequired[UUID]
    category_id: NotRequired[UUID]
    position: NotRequired[int]
    vacancy: NotRequired[Vacancy | None]
    category: NotRequired[Category | None]


class VacancyCategoryNodeFactory(
    AbstractFactory[VacancyCategoryNodeFields, VacancyCategoryNode, VacancyCategoryNodeOrm]
):
    def make(self, fields: VacancyCategoryNodeFields | None = None) -> VacancyCategoryNode:
        data = fields or {}
        return VacancyCategoryNode(
            id=data.get("id", uuid4()),
            vacancy_id=data.get("vacancy_id", uuid4()),
            category_id=data.get("category_id", uuid4()),
            position=data.get("position", 0),
            vacancy=data.get("vacancy", None),
            category=data.get("category", None),
        )

    def make_orm(
        self,
        fields: VacancyCategoryNodeFields | None = None,
    ) -> VacancyCategoryNodeOrm:
        return VacancyCategoryNodeOrm.from_entity(self.make(fields))


class VacancyCompetencyNodeFields(TypedDict):
    id: NotRequired[UUID]
    vacancy_id: NotRequired[UUID]
    competency_id: NotRequired[UUID]
    category_id: NotRequired[UUID]
    is_required: NotRequired[bool]
    position: NotRequired[int]
    vacancy: NotRequired[Vacancy | None]
    competency: NotRequired[Competency | None]
    category: NotRequired[Category | None]


class VacancyCompetencyNodeFactory(
    AbstractFactory[
        VacancyCompetencyNodeFields,
        VacancyCompetencyNode,
        VacancyCompetencyNodeOrm,
    ]
):
    def make(
        self,
        fields: VacancyCompetencyNodeFields | None = None,
    ) -> VacancyCompetencyNode:
        data = fields or {}
        return VacancyCompetencyNode(
            id=data.get("id", uuid4()),
            vacancy_id=data.get("vacancy_id", uuid4()),
            competency_id=data.get("competency_id", uuid4()),
            category_id=data.get("category_id", uuid4()),
            is_required=data.get("is_required", True),
            position=data.get("position", 0),
            vacancy=data.get("vacancy", None),
            competency=data.get("competency", None),
            category=data.get("category", None),
        )

    def make_orm(
        self,
        fields: VacancyCompetencyNodeFields | None = None,
    ) -> VacancyCompetencyNodeOrm:
        return VacancyCompetencyNodeOrm.from_entity(self.make(fields))


class VacancySubCompetencyNodeFields(TypedDict):
    id: NotRequired[UUID]
    vacancy_id: NotRequired[UUID]
    sub_competency_id: NotRequired[UUID]
    competency_id: NotRequired[UUID]
    target_level: NotRequired[CompetencyLevel]
    weight: NotRequired[float]
    position: NotRequired[int]
    vacancy: NotRequired[Vacancy | None]
    sub_competency: NotRequired[SubCompetency | None]
    competency: NotRequired[Competency | None]


class VacancySubCompetencyNodeFactory(
    AbstractFactory[
        VacancySubCompetencyNodeFields,
        VacancySubCompetencyNode,
        VacancySubCompetencyNodeOrm,
    ]
):
    def make(
        self,
        fields: VacancySubCompetencyNodeFields | None = None,
    ) -> VacancySubCompetencyNode:
        data = fields or {}
        return VacancySubCompetencyNode(
            id=data.get("id", uuid4()),
            vacancy_id=data.get("vacancy_id", uuid4()),
            sub_competency_id=data.get("sub_competency_id", uuid4()),
            competency_id=data.get("competency_id", uuid4()),
            target_level=data.get("target_level", CompetencyLevel.BEGINNER),
            weight=data.get("weight", 1.0),
            position=data.get("position", 0),
            vacancy=data.get("vacancy", None),
            sub_competency=data.get("sub_competency", None),
            competency=data.get("competency", None),
        )

    def make_orm(
        self,
        fields: VacancySubCompetencyNodeFields | None = None,
    ) -> VacancySubCompetencyNodeOrm:
        return VacancySubCompetencyNodeOrm.from_entity(self.make(fields))


class VacancyGraphSuggestionFields(TypedDict):
    id: NotRequired[UUID]
    vacancy_id: NotRequired[UUID]
    stage: NotRequired[SuggestionStage]
    entity_type: NotRequired[SuggestionEntityType]
    status: NotRequired[SuggestionStatus]
    name: NotRequired[str]
    description: NotRequired[str]
    reason: NotRequired[str]
    parent_category_id: NotRequired[UUID | None]
    parent_competency_id: NotRequired[UUID | None]
    is_required: NotRequired[bool | None]
    target_level: NotRequired[CompetencyLevel | None]
    weight: NotRequired[float | None]


class VacancyGraphSuggestionFactory(
    AbstractFactory[VacancyGraphSuggestionFields, VacancyGraphSuggestion, VacancySuggestionOrm]
):
    def make(self, fields: VacancyGraphSuggestionFields | None = None) -> VacancyGraphSuggestion:
        data = fields or {}
        return VacancyGraphSuggestion(
            id=data.get("id", uuid4()),
            vacancy_id=data.get("vacancy_id", uuid4()),
            stage=data.get("stage", SuggestionStage.CATEGORY),
            entity_type=data.get("entity_type", SuggestionEntityType.SUB_COMPETENCY),
            status=data.get("status", SuggestionStatus.PENDING),
            name=data.get("name", "SQL"),
            description=data.get("description", "PostgreSQL"),
            reason=data.get("reason", "Mentioned in requirements"),
            parent_category_id=data.get("parent_category_id", None),
            parent_competency_id=data.get("parent_competency_id", None),
            is_required=data.get("is_required", None),
            target_level=data.get("target_level", None),
            weight=data.get("weight", None),
        )

    def make_orm(self, fields: VacancyGraphSuggestionFields | None = None) -> VacancySuggestionOrm:
        return VacancySuggestionOrm.from_entity(self.make(fields))


class CandidateFields(TypedDict):
    id: NotRequired[UUID]
    external_id: NotRequired[str]
    vacancy_id: NotRequired[UUID]
    status: NotRequired[AssessmentStatus]
    last_assessment_at: NotRequired[datetime | None]
    achievements: NotRequired[list[CandidateSubCompetencyAchievement]]
    test_results: NotRequired[list[TestResult]]


class CandidateFactory(AbstractFactory[CandidateFields, Candidate, CandidateOrm]):
    def make(self, fields: CandidateFields | None = None) -> Candidate:
        data = fields or {}
        return Candidate(
            id=data.get("id", uuid4()),
            external_id=data.get("external_id", "candidate-1"),
            vacancy_id=data.get("vacancy_id", uuid4()),
            status=data.get("status", AssessmentStatus.PENDING),
            last_assessment_at=data.get("last_assessment_at", None),
            achievements=data.get("achievements", []),
            test_results=data.get("test_results", []),
        )

    def make_orm(self, fields: CandidateFields | None = None) -> CandidateOrm:
        return CandidateOrm.from_entity(self.make(fields))


class CandidateAchievementFields(TypedDict):
    id: NotRequired[UUID]
    candidate_id: NotRequired[UUID]
    sub_competency_id: NotRequired[UUID]
    achieved_at: NotRequired[datetime]


class CandidateAchievementFactory(
    AbstractFactory[CandidateAchievementFields, CandidateSubCompetencyAchievement, object]
):
    def make(
        self,
        fields: CandidateAchievementFields | None = None,
    ) -> CandidateSubCompetencyAchievement:
        data = fields or {}
        return CandidateSubCompetencyAchievement(
            id=data.get("id", uuid4()),
            candidate_id=data.get("candidate_id", uuid4()),
            sub_competency_id=data.get("sub_competency_id", uuid4()),
            achieved_at=data.get("achieved_at", datetime.now(UTC)),
        )

    def make_orm(self, fields: CandidateAchievementFields | None = None) -> object:
        raise NotImplementedError("Candidate achievement has no direct ORM mapper")


class TaskFields(TypedDict):
    id: NotRequired[UUID]
    external_id: NotRequired[str]
    title: NotRequired[str]
    description: NotRequired[str]
    type: NotRequired[TaskType]
    mapping_validated: NotRequired[bool]
    mapping_status: NotRequired[TaskMappingStatus]
    mapping_error_message: NotRequired[str | None]
    sub_competency_mappings: NotRequired[list[TaskSubCompetencyMapping]]


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
            sub_competency_mappings=data.get("sub_competency_mappings", []),
        )

    def make_orm(self, fields: TaskFields | None = None) -> TaskOrm:
        return TaskOrm.from_entity(self.make(fields))


class TaskSubCompetencyMappingFields(TypedDict):
    id: NotRequired[UUID]
    task_id: NotRequired[UUID]
    sub_competency_id: NotRequired[UUID]
    weight: NotRequired[float]
    position: NotRequired[int]
    sub_competency: NotRequired[SubCompetency | None]


class TaskSubCompetencyMappingFactory(
    AbstractFactory[TaskSubCompetencyMappingFields, TaskSubCompetencyMapping, object]
):
    def make(
        self,
        fields: TaskSubCompetencyMappingFields | None = None,
    ) -> TaskSubCompetencyMapping:
        data = fields or {}
        return TaskSubCompetencyMapping(
            id=data.get("id", uuid4()),
            task_id=data.get("task_id", UUID(int=0)),
            sub_competency_id=data.get("sub_competency_id", uuid4()),
            weight=data.get("weight", 1.0),
            position=data.get("position", 0),
            sub_competency=data.get("sub_competency", None),
        )

    def make_orm(self, fields: TaskSubCompetencyMappingFields | None = None) -> object:
        raise NotImplementedError("Task mapping has no direct ORM mapper function")


class TestResultFields(TypedDict):
    id: NotRequired[UUID]
    candidate_id: NotRequired[UUID]
    task_id: NotRequired[UUID]
    passed: NotRequired[bool]
    score: NotRequired[float]
    attempts: NotRequired[int]
    code_submitted: NotRequired[str | None]
    question_answers: NotRequired[list[TestResultQuestionAnswer]]
    llm_assessment: NotRequired[TestResultLLMAssessment | None]


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
            question_answers=data.get("question_answers", []),
            llm_assessment=data.get("llm_assessment", None),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def make_orm(self, fields: TestResultFields | None = None) -> TestResultOrm:
        return TestResultOrm.from_entity(self.make(fields))


class TestResultQuestionAnswerFields(TypedDict):
    id: NotRequired[UUID]
    test_result_id: NotRequired[UUID]
    question: NotRequired[str]
    answer: NotRequired[str]
    position: NotRequired[int]


class TestResultQuestionAnswerFactory(
    AbstractFactory[TestResultQuestionAnswerFields, TestResultQuestionAnswer, object]
):
    def make(
        self,
        fields: TestResultQuestionAnswerFields | None = None,
    ) -> TestResultQuestionAnswer:
        data = fields or {}
        return TestResultQuestionAnswer(
            id=data.get("id", uuid4()),
            test_result_id=data.get("test_result_id", uuid4()),
            question=data.get("question", "Q?"),
            answer=data.get("answer", "A"),
            position=data.get("position", 0),
        )

    def make_orm(self, fields: TestResultQuestionAnswerFields | None = None) -> object:
        raise NotImplementedError("Question answer has no direct ORM mapper function")


class TestResultLLMFeedbackItemFields(TypedDict):
    id: NotRequired[UUID]
    assessment_id: NotRequired[UUID]
    type: NotRequired[LLMFeedbackType]
    value: NotRequired[str]
    position: NotRequired[int]


class TestResultLLMFeedbackItemFactory(
    AbstractFactory[TestResultLLMFeedbackItemFields, TestResultLLMFeedbackItem, object]
):
    def make(
        self,
        fields: TestResultLLMFeedbackItemFields | None = None,
    ) -> TestResultLLMFeedbackItem:
        data = fields or {}
        return TestResultLLMFeedbackItem(
            id=data.get("id", uuid4()),
            assessment_id=data.get("assessment_id", uuid4()),
            type=data.get("type", LLMFeedbackType.POSITIVE),
            value=data.get("value", "Good"),
            position=data.get("position", 0),
        )

    def make_orm(self, fields: TestResultLLMFeedbackItemFields | None = None) -> object:
        raise NotImplementedError("Feedback item has no direct ORM mapper function")


class TestResultLLMAssessmentFields(TypedDict):
    id: NotRequired[UUID]
    test_result_id: NotRequired[UUID]
    passed: NotRequired[bool]
    score: NotRequired[float]
    feedback: NotRequired[str]
    criteria_version: NotRequired[str]
    raw_test_score: NotRequired[float]
    penalized_test_score: NotRequired[float]
    attempt_penalty_applied: NotRequired[bool]
    final_score: NotRequired[float]
    feedback_items: NotRequired[list[TestResultLLMFeedbackItem]]


class TestResultLLMAssessmentFactory(
    AbstractFactory[TestResultLLMAssessmentFields, TestResultLLMAssessment, object]
):
    def make(
        self,
        fields: TestResultLLMAssessmentFields | None = None,
    ) -> TestResultLLMAssessment:
        data = fields or {}
        return TestResultLLMAssessment(
            id=data.get("id", uuid4()),
            test_result_id=data.get("test_result_id", uuid4()),
            passed=data.get("passed", False),
            score=data.get("score", 0.0),
            feedback=data.get("feedback", ""),
            criteria_version=data.get("criteria_version", ""),
            raw_test_score=data.get("raw_test_score", 0.0),
            penalized_test_score=data.get("penalized_test_score", 0.0),
            attempt_penalty_applied=data.get("attempt_penalty_applied", False),
            final_score=data.get("final_score", 0.0),
            feedback_items=data.get("feedback_items", []),
        )

    def make_orm(self, fields: TestResultLLMAssessmentFields | None = None) -> object:
        raise NotImplementedError("LLM assessment has no direct ORM mapper function")


class WebhookEventFields(TypedDict):
    id: NotRequired[UUID]
    event_id: NotRequired[str]
    vacancy_id: NotRequired[UUID]
    candidate_external_id: NotRequired[str]
    task_external_id: NotRequired[str]
    payload: NotRequired[WebhookEventPayload | dict[str, object]]


class WebhookEventFactory(AbstractFactory[WebhookEventFields, WebhookEvent, WebhookEventOrm]):
    def make(self, fields: WebhookEventFields | None = None) -> WebhookEvent:
        data = fields or {}
        payload = data.get("payload", WebhookEventPayload(data={"k": "v"}))
        return WebhookEvent(
            id=data.get("id", uuid4()),
            event_id=data.get("event_id", "evt-1"),
            vacancy_id=data.get("vacancy_id", uuid4()),
            candidate_external_id=data.get("candidate_external_id", "candidate-1"),
            task_external_id=data.get("task_external_id", "task-1"),
            payload=payload,  # type: ignore[arg-type]
        )

    def make_orm(self, fields: WebhookEventFields | None = None) -> WebhookEventOrm:
        return WebhookEventOrm.from_entity(self.make(fields))


class RankingSnapshotFields(TypedDict):
    id: NotRequired[UUID]
    vacancy_id: NotRequired[UUID]
    payload: NotRequired[RankingSnapshotPayload | dict[str, object]]
    calculated_at: NotRequired[datetime]


class RankingSnapshotFactory(
    AbstractFactory[RankingSnapshotFields, RankingSnapshot, RankingSnapshotOrm]
):
    def make(self, fields: RankingSnapshotFields | None = None) -> RankingSnapshot:
        data = fields or {}
        payload = data.get("payload", RankingSnapshotPayload(data={"items": []}))
        return RankingSnapshot(
            id=data.get("id", uuid4()),
            vacancy_id=data.get("vacancy_id", uuid4()),
            payload=payload,  # type: ignore[arg-type]
            calculated_at=data.get("calculated_at", datetime.now(UTC)),
        )

    def make_orm(self, fields: RankingSnapshotFields | None = None) -> RankingSnapshotOrm:
        return RankingSnapshotOrm.from_entity(self.make(fields))
