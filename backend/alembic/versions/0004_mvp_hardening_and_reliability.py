"""MVP hardening and reliability primitives.

Revision ID: 0004_mvp_hardening_and_reliability
Revises: 0003_auth_users_and_refresh_tokens
Create Date: 2026-03-29 22:58:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_mvp_hardening_and_reliability"
down_revision = "0003_auth_users_and_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    webhook_event_status = postgresql.ENUM(
        "processing",
        "processed",
        "failed",
        name="webhook_event_status",
        create_type=False,
    )
    webhook_event_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_id", sa.String(length=200), nullable=False, unique=True),
        sa.Column(
            "vacancy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("candidate_external_id", sa.String(length=100), nullable=False),
        sa.Column("task_external_id", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            webhook_event_status,
            nullable=False,
            server_default="processing",
        ),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "candidate_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "test_result_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("test_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        "ranking_snapshots",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "vacancy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("ranking_snapshots")
    op.drop_table("webhook_events")
    sa.Enum(name="webhook_event_status").drop(op.get_bind(), checkfirst=True)
