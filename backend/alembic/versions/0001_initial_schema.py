"""Initial schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-29 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    vacancy_status = postgresql.ENUM(
        "draft",
        "extracting",
        "ready",
        "failed",
        name="vacancy_status",
        create_type=False,
    )
    assessment_status = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="assessment_status",
        create_type=False,
    )
    task_type = postgresql.ENUM(
        "code",
        "test",
        name="task_type",
        create_type=False,
    )
    task_mapping_status = postgresql.ENUM(
        "pending",
        "completed",
        "failed",
        name="task_mapping_status",
        create_type=False,
    )

    vacancy_status.create(op.get_bind(), checkfirst=True)
    assessment_status.create(op.get_bind(), checkfirst=True)
    task_type.create(op.get_bind(), checkfirst=True)
    task_mapping_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "description", sa.String(length=500), nullable=False, server_default=""
        ),
        sa.Column("emoji", sa.String(length=10), nullable=False, server_default="📋"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "vacancies",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=5000), nullable=False),
        sa.Column("status", vacancy_status, nullable=False, server_default="draft"),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column(
            "vacancy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            assessment_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("last_assessment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "description", sa.String(length=5000), nullable=False, server_default=""
        ),
        sa.Column("type", task_type, nullable=False, server_default="code"),
        sa.Column(
            "mapping_validated", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "mapping_status",
            task_mapping_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("mapping_error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "competencies",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "category_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "description", sa.String(length=500), nullable=False, server_default=""
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "sub_competencies",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "competency_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("competencies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "description", sa.String(length=500), nullable=False, server_default=""
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "candidate_sub_competency_achievements",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "candidate_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sub_competency_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("sub_competencies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "achieved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "candidate_id",
            "sub_competency_id",
            name="uq_candidate_sub_competency_achievement",
        ),
    )

    op.create_table(
        "task_sub_competency_mappings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sub_competency_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("sub_competencies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("task_id", "position", name="uq_task_mapping_position"),
        sa.UniqueConstraint(
            "task_id", "sub_competency_id", name="uq_task_sub_competency_mapping"
        ),
    )

    op.create_table(
        "test_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "candidate_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("code_submitted", sa.String(length=50000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "test_result_question_answers",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "test_result_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("test_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question", sa.String(length=2000), nullable=False, server_default=""
        ),
        sa.Column("answer", sa.String(length=10000), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "test_result_id",
            "position",
            name="uq_test_result_question_answer_position",
        ),
    )

    op.create_table(
        "test_result_llm_assessments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "test_result_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("test_results.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "feedback", sa.String(length=5000), nullable=False, server_default=""
        ),
        sa.Column(
            "criteria_version", sa.String(length=100), nullable=False, server_default=""
        ),
        sa.Column("raw_test_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "penalized_test_score", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "attempt_penalty_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0.0"),
    )

    op.create_table(
        "test_result_llm_strengths",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "assessment_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("test_result_llm_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "assessment_id", "position", name="uq_llm_strength_position"
        ),
    )

    op.create_table(
        "test_result_llm_issues",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "assessment_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("test_result_llm_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("assessment_id", "position", name="uq_llm_issue_position"),
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS test_result_llm_issues CASCADE")
    op.execute("DROP TABLE IF EXISTS test_result_llm_strengths CASCADE")
    op.execute("DROP TABLE IF EXISTS test_result_llm_assessments CASCADE")
    op.execute("DROP TABLE IF EXISTS test_result_question_answers CASCADE")
    op.execute("DROP TABLE IF EXISTS test_results CASCADE")
    op.execute("DROP TABLE IF EXISTS task_sub_competency_mappings CASCADE")
    op.execute("DROP TABLE IF EXISTS candidate_sub_competency_achievements CASCADE")
    op.execute("DROP TABLE IF EXISTS sub_competencies CASCADE")
    op.execute("DROP TABLE IF EXISTS competencies CASCADE")
    op.execute("DROP TABLE IF EXISTS tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS candidates CASCADE")
    op.execute("DROP TABLE IF EXISTS vacancies CASCADE")
    op.execute("DROP TABLE IF EXISTS categories CASCADE")

    sa.Enum(name="task_mapping_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="task_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="assessment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="vacancy_status").drop(op.get_bind(), checkfirst=True)
