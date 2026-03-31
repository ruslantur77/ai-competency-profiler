"""Unify test result LLM feedback items.

Revision ID: 0006_unify_test_result_llm_feedback
Revises: 0005_seed_test_competency_ontology
Create Date: 2026-03-31 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_unify_test_result_llm_feedback"
down_revision = "0005_seed_test_competency_ontology"
branch_labels = None
depends_on = None


def upgrade() -> None:
    llm_feedback_type = postgresql.ENUM(
        "positive",
        "negative",
        name="llm_feedback_type",
        create_type=False,
    )
    llm_feedback_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "test_result_llm_feedbacks",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "assessment_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("test_result_llm_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", llm_feedback_type, nullable=False),
        sa.Column("value", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "assessment_id", "position", name="uq_llm_feedback_position"
        ),
    )

    op.execute(
        """
        INSERT INTO test_result_llm_feedbacks (id, assessment_id, type, value, position)
        SELECT id, assessment_id, 'positive'::llm_feedback_type, value, position
        FROM test_result_llm_strengths
        """
    )

    op.execute(
        """
        INSERT INTO test_result_llm_feedbacks (id, assessment_id, type, value, position)
        SELECT
            i.id,
            i.assessment_id,
            'negative'::llm_feedback_type,
            i.value,
            i.position + COALESCE(s.max_position, -1) + 1
        FROM test_result_llm_issues i
        LEFT JOIN (
            SELECT assessment_id, MAX(position) AS max_position
            FROM test_result_llm_strengths
            GROUP BY assessment_id
        ) s ON s.assessment_id = i.assessment_id
        """
    )

    op.drop_table("test_result_llm_issues")
    op.drop_table("test_result_llm_strengths")


def downgrade() -> None:
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

    op.execute(
        """
        INSERT INTO test_result_llm_strengths (id, assessment_id, value, position)
        SELECT id, assessment_id, value, position
        FROM test_result_llm_feedbacks
        WHERE type = 'positive'
        """
    )

    op.execute(
        """
        INSERT INTO test_result_llm_issues (id, assessment_id, value, position)
        SELECT id, assessment_id, value, position
        FROM test_result_llm_feedbacks
        WHERE type = 'negative'
        """
    )

    op.drop_table("test_result_llm_feedbacks")
    sa.Enum(name="llm_feedback_type").drop(op.get_bind(), checkfirst=True)
