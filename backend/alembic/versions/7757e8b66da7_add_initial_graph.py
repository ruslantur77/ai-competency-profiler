"""add_initial_graph.

Revision ID: 7757e8b66da7
Revises: dbf5d903c225
Create Date: 2026-04-05 13:23:11.201684

"""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7757e8b66da7"
down_revision = "dbf5d903c225"
branch_labels = None
depends_on = None


CATEGORY_IDS = {
    "backend_dev": UUID("11111111-1111-1111-1111-111111111111"),
    "data_storage": UUID("22222222-2222-2222-2222-222222222222"),
    "infrastructure": UUID("33333333-3333-3333-3333-333333333333"),
}

COMPETENCY_IDS = {
    "api_design": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"),
    "python_backend": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"),
    "sql_modeling": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"),
    "containers": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4"),
}

SUB_COMPETENCY_IDS = {
    "rest": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"),
    "auth": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2"),
    "async_python": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3"),
    "typing": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb4"),
    "sql_indexes": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb5"),
    "sql_joins": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb6"),
    "docker": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb7"),
    "cicd": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb8"),
}


def upgrade() -> None:
    categories_table = sa.table(
        "categories",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.String(length=500)),
        sa.column("emoji", sa.String(length=10)),
    )

    competencies_table = sa.table(
        "competencies",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("category_id", sa.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.String(length=500)),
    )

    sub_competencies_table = sa.table(
        "sub_competencies",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("competency_id", sa.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.String(length=500)),
        sa.column("weight", sa.Float()),
        sa.column("target_level", sa.Integer()),
    )

    # categories — без изменений
    op.bulk_insert(
        categories_table,
        [
            {
                "id": CATEGORY_IDS["backend_dev"],
                "name": "Backend Development",
                "description": "Core backend engineering competencies",
                "emoji": "🧩",
            },
            {
                "id": CATEGORY_IDS["data_storage"],
                "name": "Data Storage",
                "description": "Relational and distributed data skills",
                "emoji": "🗄️",
            },
            {
                "id": CATEGORY_IDS["infrastructure"],
                "name": "Infrastructure",
                "description": "Deployment and runtime operations",
                "emoji": "🚀",
            },
        ],
    )

    # competencies — без изменений
    op.bulk_insert(
        competencies_table,
        [
            {
                "id": COMPETENCY_IDS["api_design"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "name": "API Design",
                "description": "HTTP API contracts and evolution",
            },
            {
                "id": COMPETENCY_IDS["python_backend"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "name": "Python Backend",
                "description": "Python language and backend frameworks",
            },
            {
                "id": COMPETENCY_IDS["sql_modeling"],
                "category_id": CATEGORY_IDS["data_storage"],
                "name": "SQL Modeling",
                "description": "Schema design and query optimization",
            },
            {
                "id": COMPETENCY_IDS["containers"],
                "category_id": CATEGORY_IDS["infrastructure"],
                "name": "Containers and Delivery",
                "description": "Containerization and CI/CD pipelines",
            },
        ],
    )

    # ⚠️ ОБНОВЛЕНО: добавлены weight и target_level
    op.bulk_insert(
        sub_competencies_table,
        [
            {
                "id": SUB_COMPETENCY_IDS["rest"],
                "competency_id": COMPETENCY_IDS["api_design"],
                "name": "REST principles",
                "description": "Resource modeling and HTTP semantics",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": SUB_COMPETENCY_IDS["auth"],
                "competency_id": COMPETENCY_IDS["api_design"],
                "name": "API security",
                "description": "Authentication and authorization for APIs",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": SUB_COMPETENCY_IDS["async_python"],
                "competency_id": COMPETENCY_IDS["python_backend"],
                "name": "Async programming",
                "description": "Async IO and concurrency patterns",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": SUB_COMPETENCY_IDS["typing"],
                "competency_id": COMPETENCY_IDS["python_backend"],
                "name": "Typing and architecture",
                "description": "Type hints and maintainable module design",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": SUB_COMPETENCY_IDS["sql_indexes"],
                "competency_id": COMPETENCY_IDS["sql_modeling"],
                "name": "Indexes",
                "description": "Index strategy and query plans",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": SUB_COMPETENCY_IDS["sql_joins"],
                "competency_id": COMPETENCY_IDS["sql_modeling"],
                "name": "Join optimization",
                "description": "Efficient joins and aggregation",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": SUB_COMPETENCY_IDS["docker"],
                "competency_id": COMPETENCY_IDS["containers"],
                "name": "Docker",
                "description": "Container images and runtime configuration",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": SUB_COMPETENCY_IDS["cicd"],
                "competency_id": COMPETENCY_IDS["containers"],
                "name": "CI/CD",
                "description": "Build/test/deploy automation",
                "weight": 1.0,
                "target_level": 3,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.delete(
            sa.table("sub_competencies", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(sa.column("id").in_(list(SUB_COMPETENCY_IDS.values())))
    )
    op.execute(
        sa.delete(
            sa.table("competencies", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(sa.column("id").in_(list(COMPETENCY_IDS.values())))
    )
    op.execute(
        sa.delete(sa.table("categories", sa.column("id", sa.UUID(as_uuid=True)))).where(
            sa.column("id").in_(list(CATEGORY_IDS.values()))
        )
    )
