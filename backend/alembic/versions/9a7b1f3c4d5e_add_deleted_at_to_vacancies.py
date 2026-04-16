"""add_deleted_at_to_vacancies.

Revision ID: 9a7b1f3c4d5e
Revises: 3f2a6d9c1b4e
Create Date: 2026-04-17 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9a7b1f3c4d5e"
down_revision = "3f2a6d9c1b4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vacancies",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vacancies", "deleted_at")
