"""add_ranking_demo_seed_data.

Revision ID: 3f2a6d9c1b4e
Revises: 7757e8b66da7
Create Date: 2026-04-15 21:30:00.000000

"""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3f2a6d9c1b4e"
down_revision = "7757e8b66da7"
branch_labels = None
depends_on = None


CATEGORY_IDS = {
    "backend_dev": UUID("11111111-1111-1111-1111-111111111111"),
    "data_storage": UUID("22222222-2222-2222-2222-222222222222"),
}

EXISTING_COMPETENCY_IDS = {
    "api_design": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"),
    "python_backend": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"),
    "sql_modeling": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"),
}

EXISTING_SUB_COMPETENCY_IDS = {
    "rest": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"),
    "auth": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2"),
    "async_python": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3"),
    "typing": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb4"),
    "sql_indexes": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb5"),
    "sql_joins": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb6"),
}

ADDED_COMPETENCY_IDS = {
    "system_design": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5"),
}

ADDED_SUB_COMPETENCY_IDS = {
    "tradeoffs": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb9"),
    "scalability": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbc0"),
}

VACANCY_ID = UUID("40000000-0000-0000-0000-000000000001")

CANDIDATE_IDS = {
    "strong": UUID("50000000-0000-0000-0000-000000000001"),
    "mid_a": UUID("50000000-0000-0000-0000-000000000002"),
    "mid_b": UUID("50000000-0000-0000-0000-000000000003"),
    "weak": UUID("50000000-0000-0000-0000-000000000004"),
    "fail": UUID("50000000-0000-0000-0000-000000000005"),
}

TASK_IDS = {
    "api": UUID("60000000-0000-0000-0000-000000000001"),
    "python": UUID("60000000-0000-0000-0000-000000000002"),
    "sql": UUID("60000000-0000-0000-0000-000000000003"),
    "system": UUID("60000000-0000-0000-0000-000000000004"),
}

VACANCY_CATEGORY_NODE_IDS = [
    UUID("41000000-0000-0000-0000-000000000001"),
    UUID("41000000-0000-0000-0000-000000000002"),
]

VACANCY_COMPETENCY_NODE_IDS = [
    UUID("42000000-0000-0000-0000-000000000001"),
    UUID("42000000-0000-0000-0000-000000000002"),
    UUID("42000000-0000-0000-0000-000000000003"),
    UUID("42000000-0000-0000-0000-000000000004"),
]

VACANCY_SUBCOMPETENCY_NODE_IDS = [
    UUID("43000000-0000-0000-0000-000000000001"),
    UUID("43000000-0000-0000-0000-000000000002"),
    UUID("43000000-0000-0000-0000-000000000003"),
    UUID("43000000-0000-0000-0000-000000000004"),
    UUID("43000000-0000-0000-0000-000000000005"),
    UUID("43000000-0000-0000-0000-000000000006"),
    UUID("43000000-0000-0000-0000-000000000007"),
    UUID("43000000-0000-0000-0000-000000000008"),
]

TASK_MAPPING_IDS = [
    UUID("61000000-0000-0000-0000-000000000001"),
    UUID("61000000-0000-0000-0000-000000000002"),
    UUID("61000000-0000-0000-0000-000000000003"),
    UUID("61000000-0000-0000-0000-000000000004"),
    UUID("61000000-0000-0000-0000-000000000005"),
    UUID("61000000-0000-0000-0000-000000000006"),
    UUID("61000000-0000-0000-0000-000000000007"),
    UUID("61000000-0000-0000-0000-000000000008"),
]

TEST_RESULT_IDS = [
    UUID("70000000-0000-0000-0000-000000000001"),
    UUID("70000000-0000-0000-0000-000000000002"),
    UUID("70000000-0000-0000-0000-000000000003"),
    UUID("70000000-0000-0000-0000-000000000004"),
    UUID("70000000-0000-0000-0000-000000000005"),
    UUID("70000000-0000-0000-0000-000000000006"),
    UUID("70000000-0000-0000-0000-000000000007"),
    UUID("70000000-0000-0000-0000-000000000008"),
    UUID("70000000-0000-0000-0000-000000000009"),
    UUID("70000000-0000-0000-0000-00000000000a"),
    UUID("70000000-0000-0000-0000-00000000000b"),
    UUID("70000000-0000-0000-0000-00000000000c"),
    UUID("70000000-0000-0000-0000-00000000000d"),
    UUID("70000000-0000-0000-0000-00000000000e"),
    UUID("70000000-0000-0000-0000-00000000000f"),
    UUID("70000000-0000-0000-0000-000000000010"),
    UUID("70000000-0000-0000-0000-000000000011"),
    UUID("70000000-0000-0000-0000-000000000012"),
    UUID("70000000-0000-0000-0000-000000000013"),
    UUID("70000000-0000-0000-0000-000000000014"),
]

LLM_ASSESSMENT_IDS = [
    UUID("71000000-0000-0000-0000-000000000001"),
    UUID("71000000-0000-0000-0000-000000000002"),
    UUID("71000000-0000-0000-0000-000000000003"),
    UUID("71000000-0000-0000-0000-000000000004"),
    UUID("71000000-0000-0000-0000-000000000005"),
    UUID("71000000-0000-0000-0000-000000000006"),
    UUID("71000000-0000-0000-0000-000000000007"),
    UUID("71000000-0000-0000-0000-000000000008"),
    UUID("71000000-0000-0000-0000-000000000009"),
    UUID("71000000-0000-0000-0000-00000000000a"),
    UUID("71000000-0000-0000-0000-00000000000b"),
    UUID("71000000-0000-0000-0000-00000000000c"),
    UUID("71000000-0000-0000-0000-00000000000d"),
    UUID("71000000-0000-0000-0000-00000000000e"),
    UUID("71000000-0000-0000-0000-00000000000f"),
    UUID("71000000-0000-0000-0000-000000000010"),
    UUID("71000000-0000-0000-0000-000000000011"),
    UUID("71000000-0000-0000-0000-000000000012"),
    UUID("71000000-0000-0000-0000-000000000013"),
    UUID("71000000-0000-0000-0000-000000000014"),
]

ACHIEVEMENT_IDS = [
    UUID("72000000-0000-0000-0000-000000000001"),
    UUID("72000000-0000-0000-0000-000000000002"),
    UUID("72000000-0000-0000-0000-000000000003"),
    UUID("72000000-0000-0000-0000-000000000004"),
    UUID("72000000-0000-0000-0000-000000000005"),
    UUID("72000000-0000-0000-0000-000000000006"),
    UUID("72000000-0000-0000-0000-000000000007"),
    UUID("72000000-0000-0000-0000-000000000008"),
    UUID("72000000-0000-0000-0000-000000000009"),
    UUID("72000000-0000-0000-0000-00000000000a"),
    UUID("72000000-0000-0000-0000-00000000000b"),
    UUID("72000000-0000-0000-0000-00000000000c"),
    UUID("72000000-0000-0000-0000-00000000000d"),
    UUID("72000000-0000-0000-0000-00000000000e"),
    UUID("72000000-0000-0000-0000-00000000000f"),
    UUID("72000000-0000-0000-0000-000000000010"),
    UUID("72000000-0000-0000-0000-000000000011"),
    UUID("72000000-0000-0000-0000-000000000012"),
    UUID("72000000-0000-0000-0000-000000000013"),
    UUID("72000000-0000-0000-0000-000000000014"),
    UUID("72000000-0000-0000-0000-000000000015"),
]

RANKING_SNAPSHOT_ID = UUID("73000000-0000-0000-0000-000000000001")


def _ranking_payload() -> dict[str, object]:
    return {
        "vacancy_id": str(VACANCY_ID),
        "rankings": [
            {
                "candidate_id": str(CANDIDATE_IDS["strong"]),
                "candidate_external_id": "seed-candidate-strong",
                "total_score": 100.0,
                "required_match": 1.0,
                "desired_match": 1.0,
                "required_score": 70.0,
                "desired_score": 30.0,
                "breakdown": [],
            },
            {
                "candidate_id": str(CANDIDATE_IDS["mid_a"]),
                "candidate_external_id": "seed-candidate-mid-a",
                "total_score": 80.6066,
                "required_match": 1.0,
                "desired_match": 0.353553,
                "required_score": 70.0,
                "desired_score": 10.6066,
                "breakdown": [],
            },
            {
                "candidate_id": str(CANDIDATE_IDS["mid_b"]),
                "candidate_external_id": "seed-candidate-mid-b",
                "total_score": 65.0,
                "required_match": 0.5,
                "desired_match": 1.0,
                "required_score": 35.0,
                "desired_score": 30.0,
                "breakdown": [],
            },
            {
                "candidate_id": str(CANDIDATE_IDS["weak"]),
                "candidate_external_id": "seed-candidate-weak",
                "total_score": 49.4975,
                "required_match": 0.707107,
                "desired_match": 0.0,
                "required_score": 49.4975,
                "desired_score": 0.0,
                "breakdown": [],
            },
            {
                "candidate_id": str(CANDIDATE_IDS["fail"]),
                "candidate_external_id": "seed-candidate-fail",
                "total_score": 0.0,
                "required_match": 0.0,
                "desired_match": 0.0,
                "required_score": 0.0,
                "desired_score": 0.0,
                "breakdown": [],
            },
        ],
    }


def upgrade() -> None:
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
    vacancies_table = sa.table(
        "vacancies",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=200)),
        sa.column("description", sa.String(length=5000)),
        sa.column("status", sa.String(length=20)),
        sa.column("error_message", sa.String(length=1000)),
    )
    vacancy_category_nodes_table = sa.table(
        "vacancy_category_nodes",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("vacancy_id", sa.UUID(as_uuid=True)),
        sa.column("category_id", sa.UUID(as_uuid=True)),
        sa.column("position", sa.Integer()),
    )
    vacancy_competency_nodes_table = sa.table(
        "vacancy_competency_nodes",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("vacancy_id", sa.UUID(as_uuid=True)),
        sa.column("competency_id", sa.UUID(as_uuid=True)),
        sa.column("category_id", sa.UUID(as_uuid=True)),
        sa.column("is_required", sa.Boolean()),
        sa.column("position", sa.Integer()),
    )
    vacancy_sub_competency_nodes_table = sa.table(
        "vacancy_sub_competency_nodes",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("vacancy_id", sa.UUID(as_uuid=True)),
        sa.column("sub_competency_id", sa.UUID(as_uuid=True)),
        sa.column("competency_id", sa.UUID(as_uuid=True)),
        sa.column("target_level", sa.Integer()),
        sa.column("weight", sa.Float()),
        sa.column("position", sa.Integer()),
    )
    candidates_table = sa.table(
        "candidates",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("external_id", sa.String(length=100)),
        sa.column("vacancy_id", sa.UUID(as_uuid=True)),
        sa.column("status", sa.String(length=20)),
        sa.column("last_assessment_at", sa.DateTime(timezone=True)),
    )
    tasks_table = sa.table(
        "tasks",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("external_id", sa.String(length=100)),
        sa.column("title", sa.String(length=200)),
        sa.column("description", sa.String(length=5000)),
        sa.column("type", sa.String(length=20)),
        sa.column("mapping_validated", sa.Boolean()),
        sa.column("mapping_status", sa.String(length=20)),
        sa.column("mapping_error_message", sa.String(length=1000)),
    )
    task_mappings_table = sa.table(
        "task_sub_competency_mappings",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("task_id", sa.UUID(as_uuid=True)),
        sa.column("sub_competency_id", sa.UUID(as_uuid=True)),
        sa.column("weight", sa.Float()),
        sa.column("position", sa.Integer()),
    )
    test_results_table = sa.table(
        "test_results",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("candidate_id", sa.UUID(as_uuid=True)),
        sa.column("task_id", sa.UUID(as_uuid=True)),
        sa.column("passed", sa.Boolean()),
        sa.column("score", sa.Float()),
        sa.column("attempts", sa.Integer()),
        sa.column("code_submitted", sa.String(length=50000)),
    )
    llm_assessments_table = sa.table(
        "test_result_llm_assessments",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("test_result_id", sa.UUID(as_uuid=True)),
        sa.column("passed", sa.Boolean()),
        sa.column("score", sa.Float()),
        sa.column("feedback", sa.String(length=5000)),
        sa.column("criteria_version", sa.String(length=100)),
        sa.column("raw_test_score", sa.Float()),
        sa.column("penalized_test_score", sa.Float()),
        sa.column("attempt_penalty_applied", sa.Boolean()),
        sa.column("final_score", sa.Float()),
    )
    achievements_table = sa.table(
        "candidate_sub_competency_achievements",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("candidate_id", sa.UUID(as_uuid=True)),
        sa.column("sub_competency_id", sa.UUID(as_uuid=True)),
    )
    ranking_snapshots_table = sa.table(
        "ranking_snapshots",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("vacancy_id", sa.UUID(as_uuid=True)),
        sa.column("payload", sa.JSON()),
    )

    op.bulk_insert(
        competencies_table,
        [
            {
                "id": ADDED_COMPETENCY_IDS["system_design"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "name": "System Design",
                "description": "Designing scalable and resilient service architecture",
            },
        ],
    )

    op.bulk_insert(
        sub_competencies_table,
        [
            {
                "id": ADDED_SUB_COMPETENCY_IDS["tradeoffs"],
                "competency_id": ADDED_COMPETENCY_IDS["system_design"],
                "name": "Architecture trade-offs",
                "description": "Balancing complexity, cost, latency and reliability",
                "weight": 1.0,
                "target_level": 3,
            },
            {
                "id": ADDED_SUB_COMPETENCY_IDS["scalability"],
                "competency_id": ADDED_COMPETENCY_IDS["system_design"],
                "name": "Scalability patterns",
                "description": "Horizontal scaling, caching and fault isolation",
                "weight": 1.0,
                "target_level": 3,
            },
        ],
    )

    op.bulk_insert(
        vacancies_table,
        [
            {
                "id": VACANCY_ID,
                "name": "Seed: Backend Engineer (Ranking Demo)",
                "description": (
                    "Demo vacancy for candidate ranking with deterministic mock data."
                ),
                "status": "ready",
                "error_message": None,
            }
        ],
    )

    op.bulk_insert(
        vacancy_category_nodes_table,
        [
            {
                "id": VACANCY_CATEGORY_NODE_IDS[0],
                "vacancy_id": VACANCY_ID,
                "category_id": CATEGORY_IDS["backend_dev"],
                "position": 1,
            },
            {
                "id": VACANCY_CATEGORY_NODE_IDS[1],
                "vacancy_id": VACANCY_ID,
                "category_id": CATEGORY_IDS["data_storage"],
                "position": 2,
            },
        ],
    )

    op.bulk_insert(
        vacancy_competency_nodes_table,
        [
            {
                "id": VACANCY_COMPETENCY_NODE_IDS[0],
                "vacancy_id": VACANCY_ID,
                "competency_id": EXISTING_COMPETENCY_IDS["api_design"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "is_required": True,
                "position": 1,
            },
            {
                "id": VACANCY_COMPETENCY_NODE_IDS[1],
                "vacancy_id": VACANCY_ID,
                "competency_id": EXISTING_COMPETENCY_IDS["python_backend"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "is_required": True,
                "position": 2,
            },
            {
                "id": VACANCY_COMPETENCY_NODE_IDS[2],
                "vacancy_id": VACANCY_ID,
                "competency_id": EXISTING_COMPETENCY_IDS["sql_modeling"],
                "category_id": CATEGORY_IDS["data_storage"],
                "is_required": False,
                "position": 3,
            },
            {
                "id": VACANCY_COMPETENCY_NODE_IDS[3],
                "vacancy_id": VACANCY_ID,
                "competency_id": ADDED_COMPETENCY_IDS["system_design"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "is_required": False,
                "position": 4,
            },
        ],
    )

    op.bulk_insert(
        vacancy_sub_competency_nodes_table,
        [
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[0],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["rest"],
                "competency_id": EXISTING_COMPETENCY_IDS["api_design"],
                "target_level": 3,
                "weight": 1.0,
                "position": 1,
            },
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[1],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["auth"],
                "competency_id": EXISTING_COMPETENCY_IDS["api_design"],
                "target_level": 3,
                "weight": 1.0,
                "position": 2,
            },
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[2],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["async_python"],
                "competency_id": EXISTING_COMPETENCY_IDS["python_backend"],
                "target_level": 3,
                "weight": 1.0,
                "position": 3,
            },
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[3],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["typing"],
                "competency_id": EXISTING_COMPETENCY_IDS["python_backend"],
                "target_level": 3,
                "weight": 1.0,
                "position": 4,
            },
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[4],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["sql_indexes"],
                "competency_id": EXISTING_COMPETENCY_IDS["sql_modeling"],
                "target_level": 2,
                "weight": 1.0,
                "position": 5,
            },
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[5],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["sql_joins"],
                "competency_id": EXISTING_COMPETENCY_IDS["sql_modeling"],
                "target_level": 2,
                "weight": 1.0,
                "position": 6,
            },
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[6],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": ADDED_SUB_COMPETENCY_IDS["tradeoffs"],
                "competency_id": ADDED_COMPETENCY_IDS["system_design"],
                "target_level": 2,
                "weight": 1.0,
                "position": 7,
            },
            {
                "id": VACANCY_SUBCOMPETENCY_NODE_IDS[7],
                "vacancy_id": VACANCY_ID,
                "sub_competency_id": ADDED_SUB_COMPETENCY_IDS["scalability"],
                "competency_id": ADDED_COMPETENCY_IDS["system_design"],
                "target_level": 2,
                "weight": 1.0,
                "position": 8,
            },
        ],
    )

    op.bulk_insert(
        candidates_table,
        [
            {
                "id": CANDIDATE_IDS["strong"],
                "external_id": "seed-candidate-strong",
                "vacancy_id": VACANCY_ID,
                "status": "completed",
                "last_assessment_at": None,
            },
            {
                "id": CANDIDATE_IDS["mid_a"],
                "external_id": "seed-candidate-mid-a",
                "vacancy_id": VACANCY_ID,
                "status": "completed",
                "last_assessment_at": None,
            },
            {
                "id": CANDIDATE_IDS["mid_b"],
                "external_id": "seed-candidate-mid-b",
                "vacancy_id": VACANCY_ID,
                "status": "completed",
                "last_assessment_at": None,
            },
            {
                "id": CANDIDATE_IDS["weak"],
                "external_id": "seed-candidate-weak",
                "vacancy_id": VACANCY_ID,
                "status": "completed",
                "last_assessment_at": None,
            },
            {
                "id": CANDIDATE_IDS["fail"],
                "external_id": "seed-candidate-fail",
                "vacancy_id": VACANCY_ID,
                "status": "failed",
                "last_assessment_at": None,
            },
        ],
    )

    op.bulk_insert(
        tasks_table,
        [
            {
                "id": TASK_IDS["api"],
                "external_id": "seed-task-api",
                "title": "API Contract and Security",
                "description": "Design REST contract and secure endpoints.",
                "type": "code",
                "mapping_validated": True,
                "mapping_status": "completed",
                "mapping_error_message": None,
            },
            {
                "id": TASK_IDS["python"],
                "external_id": "seed-task-python",
                "title": "Async Python Service",
                "description": "Implement async worker and typed module boundaries.",
                "type": "code",
                "mapping_validated": True,
                "mapping_status": "completed",
                "mapping_error_message": None,
            },
            {
                "id": TASK_IDS["sql"],
                "external_id": "seed-task-sql",
                "title": "SQL Performance Tuning",
                "description": "Improve query plans with indexes and join strategy.",
                "type": "test",
                "mapping_validated": True,
                "mapping_status": "completed",
                "mapping_error_message": None,
            },
            {
                "id": TASK_IDS["system"],
                "external_id": "seed-task-system",
                "title": "System Design Case",
                "description": "Propose scalable architecture and justify trade-offs.",
                "type": "test",
                "mapping_validated": True,
                "mapping_status": "completed",
                "mapping_error_message": None,
            },
        ],
    )

    op.bulk_insert(
        task_mappings_table,
        [
            {
                "id": TASK_MAPPING_IDS[0],
                "task_id": TASK_IDS["api"],
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["rest"],
                "weight": 1.0,
                "position": 1,
            },
            {
                "id": TASK_MAPPING_IDS[1],
                "task_id": TASK_IDS["api"],
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["auth"],
                "weight": 1.0,
                "position": 2,
            },
            {
                "id": TASK_MAPPING_IDS[2],
                "task_id": TASK_IDS["python"],
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["async_python"],
                "weight": 1.0,
                "position": 1,
            },
            {
                "id": TASK_MAPPING_IDS[3],
                "task_id": TASK_IDS["python"],
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["typing"],
                "weight": 1.0,
                "position": 2,
            },
            {
                "id": TASK_MAPPING_IDS[4],
                "task_id": TASK_IDS["sql"],
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["sql_indexes"],
                "weight": 1.0,
                "position": 1,
            },
            {
                "id": TASK_MAPPING_IDS[5],
                "task_id": TASK_IDS["sql"],
                "sub_competency_id": EXISTING_SUB_COMPETENCY_IDS["sql_joins"],
                "weight": 1.0,
                "position": 2,
            },
            {
                "id": TASK_MAPPING_IDS[6],
                "task_id": TASK_IDS["system"],
                "sub_competency_id": ADDED_SUB_COMPETENCY_IDS["tradeoffs"],
                "weight": 1.0,
                "position": 1,
            },
            {
                "id": TASK_MAPPING_IDS[7],
                "task_id": TASK_IDS["system"],
                "sub_competency_id": ADDED_SUB_COMPETENCY_IDS["scalability"],
                "weight": 1.0,
                "position": 2,
            },
        ],
    )

    raw_results = [
        ("strong", "api", True, 95.0),
        ("strong", "python", True, 92.0),
        ("strong", "sql", True, 90.0),
        ("strong", "system", True, 93.0),
        ("mid_a", "api", True, 88.0),
        ("mid_a", "python", True, 85.0),
        ("mid_a", "sql", True, 62.0),
        ("mid_a", "system", False, 40.0),
        ("mid_b", "api", True, 86.0),
        ("mid_b", "python", False, 35.0),
        ("mid_b", "sql", True, 84.0),
        ("mid_b", "system", True, 82.0),
        ("weak", "api", False, 55.0),
        ("weak", "python", False, 52.0),
        ("weak", "sql", False, 20.0),
        ("weak", "system", False, 15.0),
        ("fail", "api", False, 10.0),
        ("fail", "python", False, 5.0),
        ("fail", "sql", False, 0.0),
        ("fail", "system", False, 0.0),
    ]

    test_rows: list[dict[str, object]] = []
    llm_rows: list[dict[str, object]] = []
    for idx, (candidate_key, task_key, passed, score) in enumerate(raw_results):
        test_result_id = TEST_RESULT_IDS[idx]
        llm_assessment_id = LLM_ASSESSMENT_IDS[idx]
        test_rows.append(
            {
                "id": test_result_id,
                "candidate_id": CANDIDATE_IDS[candidate_key],
                "task_id": TASK_IDS[task_key],
                "passed": passed,
                "score": score,
                "attempts": 1,
                "code_submitted": None,
            }
        )
        llm_rows.append(
            {
                "id": llm_assessment_id,
                "test_result_id": test_result_id,
                "passed": passed,
                "score": score,
                "feedback": "Seed evaluation",
                "criteria_version": "seed-v1",
                "raw_test_score": score,
                "penalized_test_score": score,
                "attempt_penalty_applied": False,
                "final_score": score,
            }
        )

    op.bulk_insert(test_results_table, test_rows)
    op.bulk_insert(llm_assessments_table, llm_rows)

    achievement_rows = [
        # strong candidate: all sub-competencies
        ("strong", "rest"),
        ("strong", "auth"),
        ("strong", "async_python"),
        ("strong", "typing"),
        ("strong", "sql_indexes"),
        ("strong", "sql_joins"),
        ("strong", "tradeoffs"),
        ("strong", "scalability"),
        # mid-a: full required + partial desired
        ("mid_a", "rest"),
        ("mid_a", "auth"),
        ("mid_a", "async_python"),
        ("mid_a", "typing"),
        ("mid_a", "sql_indexes"),
        # mid-b: one required competency + full desired
        ("mid_b", "rest"),
        ("mid_b", "auth"),
        ("mid_b", "sql_indexes"),
        ("mid_b", "sql_joins"),
        ("mid_b", "tradeoffs"),
        ("mid_b", "scalability"),
        # weak: sparse required coverage
        ("weak", "rest"),
        ("weak", "async_python"),
    ]

    op.bulk_insert(
        achievements_table,
        [
            {
                "id": ACHIEVEMENT_IDS[idx],
                "candidate_id": CANDIDATE_IDS[candidate_key],
                "sub_competency_id": (
                    EXISTING_SUB_COMPETENCY_IDS[sub_key]
                    if sub_key in EXISTING_SUB_COMPETENCY_IDS
                    else ADDED_SUB_COMPETENCY_IDS[sub_key]
                ),
            }
            for idx, (candidate_key, sub_key) in enumerate(achievement_rows)
        ],
    )

    op.bulk_insert(
        ranking_snapshots_table,
        [
            {
                "id": RANKING_SNAPSHOT_ID,
                "vacancy_id": VACANCY_ID,
                "payload": _ranking_payload(),
            }
        ],
    )


def downgrade() -> None:
    ranking_snapshots_table = sa.table(
        "ranking_snapshots", sa.column("id", sa.UUID(as_uuid=True))
    )
    test_results_table = sa.table(
        "test_results", sa.column("id", sa.UUID(as_uuid=True))
    )
    tasks_table = sa.table("tasks", sa.column("id", sa.UUID(as_uuid=True)))

    op.execute(
        sa.delete(ranking_snapshots_table).where(
            sa.column("id").in_([RANKING_SNAPSHOT_ID])
        )
    )

    op.execute(
        sa.delete(
            sa.table(
                "test_result_llm_assessments", sa.column("id", sa.UUID(as_uuid=True))
            )
        ).where(sa.column("id").in_(LLM_ASSESSMENT_IDS))
    )
    op.execute(
        sa.delete(test_results_table).where(sa.column("id").in_(TEST_RESULT_IDS))
    )
    op.execute(
        sa.delete(
            sa.table(
                "candidate_sub_competency_achievements",
                sa.column("id", sa.UUID(as_uuid=True)),
            )
        ).where(sa.column("id").in_(ACHIEVEMENT_IDS))
    )

    op.execute(
        sa.delete(
            sa.table(
                "task_sub_competency_mappings", sa.column("id", sa.UUID(as_uuid=True))
            )
        ).where(sa.column("id").in_(TASK_MAPPING_IDS))
    )
    op.execute(
        sa.delete(tasks_table).where(sa.column("id").in_(list(TASK_IDS.values())))
    )

    op.execute(
        sa.delete(sa.table("candidates", sa.column("id", sa.UUID(as_uuid=True)))).where(
            sa.column("id").in_(list(CANDIDATE_IDS.values()))
        )
    )

    op.execute(
        sa.delete(
            sa.table(
                "vacancy_sub_competency_nodes", sa.column("id", sa.UUID(as_uuid=True))
            )
        ).where(sa.column("id").in_(VACANCY_SUBCOMPETENCY_NODE_IDS))
    )
    op.execute(
        sa.delete(
            sa.table("vacancy_competency_nodes", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(sa.column("id").in_(VACANCY_COMPETENCY_NODE_IDS))
    )
    op.execute(
        sa.delete(
            sa.table("vacancy_category_nodes", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(sa.column("id").in_(VACANCY_CATEGORY_NODE_IDS))
    )
    op.execute(
        sa.delete(sa.table("vacancies", sa.column("id", sa.UUID(as_uuid=True)))).where(
            sa.column("id").in_([VACANCY_ID])
        )
    )

    op.execute(
        sa.delete(
            sa.table("sub_competencies", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(sa.column("id").in_(list(ADDED_SUB_COMPETENCY_IDS.values())))
    )
    op.execute(
        sa.delete(
            sa.table("competencies", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(sa.column("id").in_(list(ADDED_COMPETENCY_IDS.values())))
    )
