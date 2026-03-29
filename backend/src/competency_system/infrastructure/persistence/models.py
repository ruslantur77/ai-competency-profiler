from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from competency_system.domain.value_objects.enums import UserRole


class Base(DeclarativeBase):
    pass


class UserOrm(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=UserRole.HR,
        server_default=UserRole.HR.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    refresh_tokens: Mapped[list[RefreshTokenOrm]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
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
    is_required: Mapped[bool] = mapped_column(default=True)

    category: Mapped[CategoryOrm] = relationship(back_populates="competencies")
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
    target_level: Mapped[int] = mapped_column(default=2)  # 0-5
    weight: Mapped[float] = mapped_column(default=1.0)

    competency: Mapped[CompetencyOrm] = relationship(back_populates="sub_competencies")

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
    status: Mapped[str] = mapped_column(String(50), default="draft")
    experience: Mapped[str] = mapped_column(String(100), default="")
    key_skills: Mapped[str] = mapped_column(String(2000), default="")  # JSON as string
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relations - stored as JSON for flexibility
    categories_snapshot: Mapped[str] = mapped_column(String(10000), default="[]")
    competencies_snapshot: Mapped[str] = mapped_column(String(20000), default="[]")

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
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    category_id: Mapped[UUID] = mapped_column()
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    emoji: Mapped[str] = mapped_column(String(10), default="📋")
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
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    competency_id: Mapped[UUID] = mapped_column()
    category_id: Mapped[UUID] = mapped_column()
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
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
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    sub_competency_id: Mapped[UUID] = mapped_column()
    competency_id: Mapped[UUID] = mapped_column()
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    target_level: Mapped[int] = mapped_column(default=2)
    weight: Mapped[float] = mapped_column(default=1.0)
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
    stage: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending")

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    reason: Mapped[str] = mapped_column(String(1000), default="")

    parent_category_id: Mapped[UUID | None] = mapped_column(nullable=True)
    parent_competency_id: Mapped[UUID | None] = mapped_column(nullable=True)

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
    status: Mapped[str] = mapped_column(String(50), default="pending")
    achieved_subcompetency_ids: Mapped[str] = mapped_column(
        String(5000), default="[]"
    )  # JSON array of UUIDs

    last_assessment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TaskOrm(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(5000), default="")
    type: Mapped[str] = mapped_column(String(50), default="code")
    mapping_validated: Mapped[bool] = mapped_column(default=False)

    # JSON for flexibility
    competency_mappings: Mapped[str] = mapped_column(String(5000), default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


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
    llm_assessment: Mapped[str | None] = mapped_column(
        String(5000), nullable=True
    )  # JSON

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
