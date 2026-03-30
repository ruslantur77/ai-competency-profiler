from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from competency_system.domain.value_objects.enums import (
    AssessmentStatus,
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    TaskMappingStatus,
    TaskType,
    UserRole,
    VacancyStatus,
    WebhookEventStatus,
)

JSON_PAYLOAD = JSON().with_variant(JSONB, "postgresql")


def _enum_values(enum_cls: type[PyEnum]) -> list[str]:
    return [str(member.value) for member in enum_cls]


class Base(DeclarativeBase):
    pass


class UserOrm(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=_enum_values),
        server_default=UserRole.HR.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    refresh_tokens: Mapped[list[RefreshTokenOrm]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )


class RefreshTokenOrm(Base):
    __tablename__ = "refresh_tokens"

    jti: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[UserOrm] = relationship(back_populates="refresh_tokens", lazy="raise")


class CategoryOrm(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    emoji: Mapped[str] = mapped_column(String(10), default="📋")

    competencies: Mapped[list[CompetencyOrm]] = relationship(
        back_populates="category", cascade="all, delete-orphan", lazy="raise"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CompetencyOrm(Base):
    __tablename__ = "competencies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")

    category: Mapped[CategoryOrm] = relationship(
        back_populates="competencies", lazy="raise"
    )
    sub_competencies: Mapped[list[SubCompetencyOrm]] = relationship(
        back_populates="competency", cascade="all, delete-orphan", lazy="raise"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SubCompetencyOrm(Base):
    __tablename__ = "sub_competencies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    competency_id: Mapped[UUID] = mapped_column(
        ForeignKey("competencies.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")

    competency: Mapped[CompetencyOrm] = relationship(
        back_populates="sub_competencies", lazy="raise"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VacancyOrm(Base):
    __tablename__ = "vacancies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(5000))
    status: Mapped[VacancyStatus] = mapped_column(
        Enum(VacancyStatus, name="vacancy_status", values_callable=_enum_values),
        server_default=VacancyStatus.DRAFT.value,
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VacancyCategoryNodeOrm(Base):
    __tablename__ = "vacancy_category_nodes"
    __table_args__ = (
        UniqueConstraint("vacancy_id", "position", name="uq_vacancy_category_position"),
        UniqueConstraint("vacancy_id", "category_id", name="uq_vacancy_category_node"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VacancyCompetencyNodeOrm(Base):
    __tablename__ = "vacancy_competency_nodes"
    __table_args__ = (
        UniqueConstraint(
            "vacancy_id", "position", name="uq_vacancy_competency_position"
        ),
        UniqueConstraint(
            "vacancy_id", "competency_id", name="uq_vacancy_competency_node"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    competency_id: Mapped[UUID] = mapped_column(
        ForeignKey("competencies.id", ondelete="CASCADE")
    )
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    is_required: Mapped[bool] = mapped_column(default=True)
    position: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VacancySubCompetencyNodeOrm(Base):
    __tablename__ = "vacancy_sub_competency_nodes"
    __table_args__ = (
        UniqueConstraint(
            "vacancy_id", "position", name="uq_vacancy_subcompetency_position"
        ),
        UniqueConstraint(
            "vacancy_id",
            "sub_competency_id",
            name="uq_vacancy_sub_competency_node",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    sub_competency_id: Mapped[UUID] = mapped_column(
        ForeignKey("sub_competencies.id", ondelete="CASCADE")
    )
    competency_id: Mapped[UUID] = mapped_column(
        ForeignKey("competencies.id", ondelete="CASCADE")
    )
    target_level: Mapped[int] = mapped_column(default=2)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    position: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VacancySuggestionOrm(Base):
    __tablename__ = "vacancy_graph_suggestions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    stage: Mapped[SuggestionStage] = mapped_column(
        Enum(
            SuggestionStage,
            name="suggestion_stage",
            values_callable=_enum_values,
        )
    )
    entity_type: Mapped[SuggestionEntityType] = mapped_column(
        Enum(
            SuggestionEntityType,
            name="suggestion_entity_type",
            values_callable=_enum_values,
        )
    )
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, name="suggestion_status", values_callable=_enum_values),
        server_default=SuggestionStatus.PENDING.value,
    )

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    reason: Mapped[str] = mapped_column(String(1000), default="")

    parent_category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    parent_competency_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True
    )

    is_required: Mapped[bool | None] = mapped_column(nullable=True)
    target_level: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CandidateOrm(Base):
    __tablename__ = "candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(100), unique=True)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, name="assessment_status", values_callable=_enum_values),
        server_default=AssessmentStatus.PENDING.value,
    )
    last_assessment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    achievements: Mapped[list[CandidateSubCompetencyAchievementOrm]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", lazy="raise"
    )
    test_results: Mapped[list[TestResultOrm]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", lazy="raise"
    )


class CandidateSubCompetencyAchievementOrm(Base):
    __tablename__ = "candidate_sub_competency_achievements"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "sub_competency_id",
            name="uq_candidate_sub_competency_achievement",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE")
    )
    sub_competency_id: Mapped[UUID] = mapped_column(
        ForeignKey("sub_competencies.id", ondelete="CASCADE")
    )
    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    candidate: Mapped[CandidateOrm] = relationship(
        back_populates="achievements", lazy="raise"
    )
    sub_competency: Mapped[SubCompetencyOrm] = relationship(lazy="raise")


class TaskOrm(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(5000), default="")
    type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type", values_callable=_enum_values),
        server_default=TaskType.CODE.value,
    )
    mapping_validated: Mapped[bool] = mapped_column(default=False)
    mapping_status: Mapped[TaskMappingStatus] = mapped_column(
        Enum(
            TaskMappingStatus,
            name="task_mapping_status",
            values_callable=_enum_values,
        ),
        server_default=TaskMappingStatus.PENDING.value,
    )
    mapping_error_message: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    sub_competency_mappings: Mapped[list[TaskSubCompetencyMappingOrm]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="raise"
    )
    test_results: Mapped[list[TestResultOrm]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="raise"
    )


class TaskSubCompetencyMappingOrm(Base):
    __tablename__ = "task_sub_competency_mappings"
    __table_args__ = (
        UniqueConstraint("task_id", "position", name="uq_task_mapping_position"),
        UniqueConstraint(
            "task_id", "sub_competency_id", name="uq_task_sub_competency_mapping"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    sub_competency_id: Mapped[UUID] = mapped_column(
        ForeignKey("sub_competencies.id", ondelete="CASCADE")
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    position: Mapped[int] = mapped_column(Integer)
    task: Mapped[TaskOrm] = relationship(
        back_populates="sub_competency_mappings", lazy="raise"
    )
    sub_competency: Mapped[SubCompetencyOrm] = relationship(lazy="raise")


class TestResultOrm(Base):
    __tablename__ = "test_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE")
    )
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    passed: Mapped[bool] = mapped_column(default=False)
    score: Mapped[float] = mapped_column(default=0.0)
    attempts: Mapped[int] = mapped_column(default=1)
    code_submitted: Mapped[str | None] = mapped_column(String(50000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    task: Mapped[TaskOrm] = relationship(lazy="raise")
    candidate: Mapped[CandidateOrm] = relationship(lazy="raise")


class TestResultQuestionAnswerOrm(Base):
    __tablename__ = "test_result_question_answers"
    __table_args__ = (
        UniqueConstraint(
            "test_result_id", "position", name="uq_test_result_question_answer_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    test_result_id: Mapped[UUID] = mapped_column(
        ForeignKey(TestResultOrm.id, ondelete="CASCADE")
    )
    question: Mapped[str] = mapped_column(String(2000), default="")
    answer: Mapped[str] = mapped_column(String(10000), default="")
    position: Mapped[int] = mapped_column(Integer)


class TestResultLLMAssessmentOrm(Base):
    __tablename__ = "test_result_llm_assessments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    test_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_results.id", ondelete="CASCADE"), unique=True
    )
    passed: Mapped[bool] = mapped_column(default=False)
    score: Mapped[float] = mapped_column(default=0.0)
    feedback: Mapped[str] = mapped_column(String(5000), default="")
    criteria_version: Mapped[str] = mapped_column(String(100), default="")
    raw_test_score: Mapped[float] = mapped_column(Float, default=0.0)
    penalized_test_score: Mapped[float] = mapped_column(Float, default=0.0)
    attempt_penalty_applied: Mapped[bool] = mapped_column(default=False)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)


class TestResultLLMStrengthOrm(Base):
    __tablename__ = "test_result_llm_strengths"
    __table_args__ = (
        UniqueConstraint("assessment_id", "position", name="uq_llm_strength_position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_result_llm_assessments.id", ondelete="CASCADE")
    )
    value: Mapped[str] = mapped_column(String(2000), default="")
    position: Mapped[int] = mapped_column(Integer)


class TestResultLLMIssueOrm(Base):
    __tablename__ = "test_result_llm_issues"
    __table_args__ = (
        UniqueConstraint("assessment_id", "position", name="uq_llm_issue_position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_result_llm_assessments.id", ondelete="CASCADE")
    )
    value: Mapped[str] = mapped_column(String(2000), default="")
    position: Mapped[int] = mapped_column(Integer)


class WebhookEventOrm(Base):
    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[str] = mapped_column(String(200), unique=True)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    candidate_external_id: Mapped[str] = mapped_column(String(100))
    task_external_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[WebhookEventStatus] = mapped_column(
        Enum(
            WebhookEventStatus,
            name="webhook_event_status",
            values_callable=_enum_values,
        ),
        server_default=WebhookEventStatus.PROCESSING.value,
    )
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    candidate_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    test_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("test_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSON_PAYLOAD, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RankingSnapshotOrm(Base):
    __tablename__ = "ranking_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"), unique=True
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSON_PAYLOAD, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
