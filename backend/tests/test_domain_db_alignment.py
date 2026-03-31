from __future__ import annotations

from dataclasses import fields
from typing import Any

from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    RankingSnapshot,
    RefreshToken,
    SubCompetency,
    Task,
    TestResult,
    User,
    Vacancy,
    VacancyGraphSuggestion,
    WebhookEvent,
)
from competency_system.infrastructure.persistence.models import (
    Base,
    CandidateOrm,
    CategoryOrm,
    CompetencyOrm,
    RankingSnapshotOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    TestResultOrm,
    UserOrm,
    VacancyOrm,
    VacancySuggestionOrm,
    WebhookEventOrm,
)

BASE_ENTITY_FIELDS = {"id", "created_at", "updated_at"}

DOMAIN_DB_SPECS: list[dict[str, Any]] = [
    {
        "domain": Category,
        "orm": CategoryOrm,
        "derived": {"competencies"},
    },
    {
        "domain": Competency,
        "orm": CompetencyOrm,
        "derived": {"sub_competencies", "is_required"},
    },
    {
        "domain": SubCompetency,
        "orm": SubCompetencyOrm,
        "derived": {"target_level", "weight"},
    },
    {
        "domain": Vacancy,
        "orm": VacancyOrm,
        "derived": {
            "categories",
            "competencies",
            "category_nodes",
            "competency_nodes",
            "sub_competency_nodes",
        },
    },
    {
        "domain": Candidate,
        "orm": CandidateOrm,
        "derived": {"achievements", "achieved_subcompetency_ids"},
        "aliases": {"assessment_status": "status"},
    },
    {
        "domain": Task,
        "orm": TaskOrm,
        "derived": {"competency_mappings", "sub_competency_mappings"},
    },
    {
        "domain": TestResult,
        "orm": TestResultOrm,
        "derived": {"question_answers", "llm_assessment"},
    },
    {
        "domain": VacancyGraphSuggestion,
        "orm": VacancySuggestionOrm,
    },
    {
        "domain": User,
        "orm": UserOrm,
    },
    {
        "domain": RefreshToken,
        "orm": RefreshTokenOrm,
    },
    {
        "domain": WebhookEvent,
        "orm": WebhookEventOrm,
    },
    {
        "domain": RankingSnapshot,
        "orm": RankingSnapshotOrm,
    },
]


def test_domain_fields_are_backed_by_db_or_explicitly_derived() -> None:
    for spec in DOMAIN_DB_SPECS:
        domain_cls = spec["domain"]
        orm_cls = spec["orm"]
        aliases = spec.get("aliases", {})
        derived = set(spec.get("derived", set()))

        domain_fields = {
            field.name for field in fields(domain_cls)
        } - BASE_ENTITY_FIELDS
        orm_columns = set(orm_cls.__table__.columns.keys())
        covered = set(derived)

        for field_name in domain_fields:
            if field_name in orm_columns:
                covered.add(field_name)
                continue
            alias = aliases.get(field_name)
            if alias is not None and alias in orm_columns:
                covered.add(field_name)

        missing = domain_fields - covered
        assert not missing, (
            f"{domain_cls.__name__} has unmapped fields: {sorted(missing)}"
        )


def test_derived_fields_use_existing_tables() -> None:
    known_tables = set(Base.metadata.tables.keys())
    # Документируем, из каких таблиц собираются derived-поля.
    derived_sources = {
        "Category.competencies": {"competencies", "sub_competencies"},
        "Competency.sub_competencies": {"sub_competencies"},
        "Competency.is_required": {"vacancy_competency_nodes"},
        "SubCompetency.target_level": {"vacancy_sub_competency_nodes"},
        "SubCompetency.weight": {"vacancy_sub_competency_nodes"},
        "Vacancy.categories": {"vacancy_category_nodes", "categories"},
        "Vacancy.competencies": {
            "vacancy_competency_nodes",
            "vacancy_sub_competency_nodes",
            "competencies",
            "sub_competencies",
        },
        "Vacancy.category_nodes": {"vacancy_category_nodes"},
        "Vacancy.competency_nodes": {"vacancy_competency_nodes"},
        "Vacancy.sub_competency_nodes": {"vacancy_sub_competency_nodes"},
        "Candidate.achieved_subcompetency_ids": {
            "candidate_sub_competency_achievements"
        },
        "Candidate.achievements": {"candidate_sub_competency_achievements"},
        "Task.competency_mappings": {"task_sub_competency_mappings"},
        "Task.sub_competency_mappings": {"task_sub_competency_mappings"},
        "TestResult.question_answers": {"test_result_question_answers"},
        "TestResult.llm_assessment": {
            "test_result_llm_assessments",
            "test_result_llm_feedbacks",
        },
    }

    for field_name, tables in derived_sources.items():
        assert tables <= known_tables, (
            f"Derived field {field_name} references unknown tables: "
            f"{sorted(tables - known_tables)}"
        )
