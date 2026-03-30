"""Vacancy graph nodes and suggestions.

Revision ID: 0002_vacancy_graph_nodes_and_suggestions
Revises: 0001_initial_schema
Create Date: 2026-03-29 17:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_vacancy_graph_nodes_and_suggestions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    suggestion_stage = postgresql.ENUM(
        "category",
        "competency",
        "sub_competency",
        name="suggestion_stage",
        create_type=False,
    )
    suggestion_entity_type = postgresql.ENUM(
        "category",
        "competency",
        "sub_competency",
        name="suggestion_entity_type",
        create_type=False,
    )
    suggestion_status = postgresql.ENUM(
        "pending",
        "approved",
        "rejected",
        name="suggestion_status",
        create_type=False,
    )

    suggestion_stage.create(op.get_bind(), checkfirst=True)
    suggestion_entity_type.create(op.get_bind(), checkfirst=True)
    suggestion_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "vacancy_category_nodes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "vacancy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint(
            "vacancy_id", "position", name="uq_vacancy_category_position"
        ),
        sa.UniqueConstraint(
            "vacancy_id", "category_id", name="uq_vacancy_category_node"
        ),
    )
    op.create_table(
        "vacancy_competency_nodes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "vacancy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "competency_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("competencies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "is_required", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint(
            "vacancy_id", "position", name="uq_vacancy_competency_position"
        ),
        sa.UniqueConstraint(
            "vacancy_id", "competency_id", name="uq_vacancy_competency_node"
        ),
    )
    op.create_table(
        "vacancy_sub_competency_nodes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "vacancy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sub_competency_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("sub_competencies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "competency_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("competencies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_level", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint(
            "vacancy_id", "position", name="uq_vacancy_subcompetency_position"
        ),
        sa.UniqueConstraint(
            "vacancy_id",
            "sub_competency_id",
            name="uq_vacancy_sub_competency_node",
        ),
    )
    op.create_table(
        "vacancy_graph_suggestions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "vacancy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", suggestion_stage, nullable=False),
        sa.Column("entity_type", suggestion_entity_type, nullable=False),
        sa.Column(
            "status", suggestion_status, nullable=False, server_default="pending"
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "description", sa.String(length=500), nullable=False, server_default=""
        ),
        sa.Column("reason", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column(
            "parent_category_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_competency_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("competencies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_required", sa.Boolean(), nullable=True),
        sa.Column("target_level", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
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


def downgrade() -> None:
    op.drop_table("vacancy_graph_suggestions")
    op.drop_table("vacancy_sub_competency_nodes")
    op.drop_table("vacancy_competency_nodes")
    op.drop_table("vacancy_category_nodes")

    sa.Enum(name="suggestion_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="suggestion_entity_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="suggestion_stage").drop(op.get_bind(), checkfirst=True)
