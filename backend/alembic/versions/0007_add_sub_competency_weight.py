"""Add ontology weight to sub_competencies.

Revision ID: 0007_add_sub_competency_weight
Revises: 0006_unify_test_result_llm_feedback
Create Date: 2026-04-03 23:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007_add_sub_competency_weight"
down_revision = "0006_unify_test_result_llm_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sub_competencies",
        sa.Column(
            "weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("sub_competencies", "weight")
