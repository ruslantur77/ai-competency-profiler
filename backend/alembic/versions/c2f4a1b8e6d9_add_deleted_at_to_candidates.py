"""add_deleted_at_to_candidates.

Revision ID: c2f4a1b8e6d9
Revises: 9a7b1f3c4d5e
Create Date: 2026-04-17 13:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c2f4a1b8e6d9"
down_revision = "9a7b1f3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidates", "deleted_at")
