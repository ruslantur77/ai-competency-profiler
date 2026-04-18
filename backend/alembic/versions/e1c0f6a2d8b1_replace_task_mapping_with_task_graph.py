"""replace_task_mapping_with_task_graph.

Revision ID: e1c0f6a2d8b1
Revises: c2f4a1b8e6d9
Create Date: 2026-04-18 12:30:00.000000

"""

from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e1c0f6a2d8b1"
down_revision = "c2f4a1b8e6d9"
branch_labels = None
depends_on = None


TASK_STATUS_VALUES = ("pending", "draft", "ready", "failed")
TASK_MAPPING_STATUS_VALUES = ("pending", "completed", "failed")


def _create_task_status_enum() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'task_status'
                    ) THEN
                        CREATE TYPE task_status AS ENUM (
                            'pending',
                            'draft',
                            'ready',
                            'failed'
                        );
                    END IF;
                END
                $$;
                """
            )
        )


def _drop_task_status_enum() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_status') THEN "
                "DROP TYPE task_status; "
                "END IF; "
                "END $$;"
            )
        )


def _create_task_mapping_status_enum() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'task_mapping_status'
                    ) THEN
                        CREATE TYPE task_mapping_status AS ENUM (
                            'pending',
                            'completed',
                            'failed'
                        );
                    END IF;
                END
                $$;
                """
            )
        )


def _drop_task_mapping_status_enum() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'task_mapping_status'
                    ) THEN
                        DROP TYPE task_mapping_status;
                    END IF;
                END
                $$;
                """
            )
        )


def upgrade() -> None:
    _create_task_status_enum()

    op.add_column(
        "tasks",
        sa.Column(
            "status",
            sa.Enum(*TASK_STATUS_VALUES, name="task_status"),
            server_default="pending",
            nullable=True,
        ),
    )
    op.add_column(
        "tasks",
        sa.Column("error_message", sa.String(length=1000), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET
                status = CASE
                    WHEN mapping_status = 'failed' THEN 'failed'
                    WHEN mapping_status = 'completed' AND mapping_validated = true
                        THEN 'ready'
                    WHEN mapping_status = 'completed' AND mapping_validated = false
                        THEN 'draft'
                    ELSE 'pending'
                END,
                error_message = mapping_error_message
            """
        )
    )

    op.alter_column("tasks", "status", nullable=False)

    op.create_table(
        "task_category_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "category_id", name="uq_task_category_node"),
        sa.UniqueConstraint("task_id", "position", name="uq_task_category_position"),
    )
    op.create_table(
        "task_competency_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["competency_id"], ["competencies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "competency_id", name="uq_task_competency_node"),
        sa.UniqueConstraint("task_id", "position", name="uq_task_competency_position"),
    )
    op.create_table(
        "task_sub_competency_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("sub_competency_id", sa.Uuid(), nullable=False),
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["competency_id"], ["competencies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sub_competency_id"], ["sub_competencies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "sub_competency_id",
            name="uq_task_sub_competency_node",
        ),
        sa.UniqueConstraint(
            "task_id", "position", name="uq_task_subcompetency_position"
        ),
    )

    bind = op.get_bind()
    rows = (
        bind.execute(
            sa.text(
                """
                SELECT
                    m.task_id,
                    m.sub_competency_id,
                    m.target_level,
                    m.weight,
                    sc.competency_id,
                    c.category_id
                FROM task_sub_competency_mappings AS m
                JOIN sub_competencies AS sc ON sc.id = m.sub_competency_id
                JOIN competencies AS c ON c.id = sc.competency_id
                ORDER BY m.task_id, m.position
                """
            )
        )
        .mappings()
        .all()
    )

    category_rows: list[dict[str, object]] = []
    competency_rows: list[dict[str, object]] = []
    sub_rows: list[dict[str, object]] = []

    seen_categories: dict[tuple[object, object], int] = {}
    seen_competencies: dict[tuple[object, object], int] = {}
    task_category_pos: dict[object, int] = {}
    task_competency_pos: dict[object, int] = {}
    task_sub_pos: dict[object, int] = {}

    for row in rows:
        task_id = row["task_id"]
        category_id = row["category_id"]
        competency_id = row["competency_id"]
        sub_competency_id = row["sub_competency_id"]

        category_key = (task_id, category_id)
        if category_key not in seen_categories:
            position = task_category_pos.get(task_id, 0)
            task_category_pos[task_id] = position + 1
            seen_categories[category_key] = position
            category_rows.append(
                {
                    "id": uuid4(),
                    "task_id": task_id,
                    "category_id": category_id,
                    "position": position,
                }
            )

        competency_key = (task_id, competency_id)
        if competency_key not in seen_competencies:
            position = task_competency_pos.get(task_id, 0)
            task_competency_pos[task_id] = position + 1
            seen_competencies[competency_key] = position
            competency_rows.append(
                {
                    "id": uuid4(),
                    "task_id": task_id,
                    "competency_id": competency_id,
                    "category_id": category_id,
                    "is_required": True,
                    "position": position,
                }
            )

        sub_position = task_sub_pos.get(task_id, 0)
        task_sub_pos[task_id] = sub_position + 1
        sub_rows.append(
            {
                "id": uuid4(),
                "task_id": task_id,
                "sub_competency_id": sub_competency_id,
                "competency_id": competency_id,
                "target_level": row["target_level"],
                "weight": row["weight"],
                "position": sub_position,
            }
        )

    if category_rows:
        op.bulk_insert(
            sa.table(
                "task_category_nodes",
                sa.column("id", sa.Uuid()),
                sa.column("task_id", sa.Uuid()),
                sa.column("category_id", sa.Uuid()),
                sa.column("position", sa.Integer()),
            ),
            category_rows,
        )
    if competency_rows:
        op.bulk_insert(
            sa.table(
                "task_competency_nodes",
                sa.column("id", sa.Uuid()),
                sa.column("task_id", sa.Uuid()),
                sa.column("competency_id", sa.Uuid()),
                sa.column("category_id", sa.Uuid()),
                sa.column("is_required", sa.Boolean()),
                sa.column("position", sa.Integer()),
            ),
            competency_rows,
        )
    if sub_rows:
        op.bulk_insert(
            sa.table(
                "task_sub_competency_nodes",
                sa.column("id", sa.Uuid()),
                sa.column("task_id", sa.Uuid()),
                sa.column("sub_competency_id", sa.Uuid()),
                sa.column("competency_id", sa.Uuid()),
                sa.column("target_level", sa.Integer()),
                sa.column("weight", sa.Float()),
                sa.column("position", sa.Integer()),
            ),
            sub_rows,
        )

    op.drop_table("task_sub_competency_mappings")

    op.drop_column("tasks", "mapping_error_message")
    op.drop_column("tasks", "mapping_status")
    op.drop_column("tasks", "mapping_validated")

    _drop_task_mapping_status_enum()


def downgrade() -> None:
    _create_task_mapping_status_enum()

    op.add_column(
        "tasks",
        sa.Column(
            "mapping_validated", sa.Boolean(), server_default="false", nullable=True
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "mapping_status",
            sa.Enum(*TASK_MAPPING_STATUS_VALUES, name="task_mapping_status"),
            server_default="pending",
            nullable=True,
        ),
    )
    op.add_column(
        "tasks",
        sa.Column("mapping_error_message", sa.String(length=1000), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET
                mapping_validated = (status = 'ready'),
                mapping_status = CASE
                    WHEN status = 'failed' THEN 'failed'
                    WHEN status IN ('ready', 'draft') THEN 'completed'
                    ELSE 'pending'
                END,
                mapping_error_message = error_message
            """
        )
    )
    op.alter_column("tasks", "mapping_validated", nullable=False)
    op.alter_column("tasks", "mapping_status", nullable=False)

    op.create_table(
        "task_sub_competency_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("sub_competency_id", sa.Uuid(), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["sub_competency_id"], ["sub_competencies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id", "sub_competency_id", name="uq_task_sub_competency_mapping"
        ),
        sa.UniqueConstraint("task_id", "position", name="uq_task_mapping_position"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO task_sub_competency_mappings (
                id, task_id, sub_competency_id, target_level, weight, position
            )
            SELECT
                id,
                task_id,
                sub_competency_id,
                target_level,
                weight,
                position
            FROM task_sub_competency_nodes
            """
        )
    )

    op.drop_table("task_sub_competency_nodes")
    op.drop_table("task_competency_nodes")
    op.drop_table("task_category_nodes")

    op.drop_column("tasks", "error_message")
    op.drop_column("tasks", "status")
    _drop_task_status_enum()
