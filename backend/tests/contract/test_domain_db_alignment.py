from __future__ import annotations

from dataclasses import fields
from typing import Any

import pytest

from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    RefreshToken,
    SubCompetency,
    Task,
    User,
    Vacancy,
    VacancyGraphSuggestion,
)
from competency_system.domain.entities import (
    TestResult as _TestResult,
)
from competency_system.infrastructure.persistence.models import (
    Base,
    CandidateOrm,
    CategoryOrm,
    CompetencyOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    UserOrm,
    VacancyOrm,
    VacancySuggestionOrm,
)
from competency_system.infrastructure.persistence.models import (
    TestResultOrm as _TestResultOrm,
)

pytestmark = pytest.mark.contract

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
        "derived": {"sub_competencies", "category"},
    },
    {
        "domain": SubCompetency,
        "orm": SubCompetencyOrm,
        "derived": {"competency"},
    },
    {
        "domain": Vacancy,
        "orm": VacancyOrm,
        "derived": {
            "candidates",
            "category_nodes",
            "competency_nodes",
            "sub_competency_nodes",
            "suggestions",
        },
    },
    {
        "domain": Candidate,
        "orm": CandidateOrm,
        "derived": {
            "vacancy",
            "achievements",
            "test_results",
            "achieved_subcompetency_ids",
            "assessment_status",
        },
        "aliases": {"assessment_status": "status"},
    },
    {
        "domain": Task,
        "orm": TaskOrm,
        "derived": {"sub_competency_mappings"},
    },
    {
        "domain": _TestResult,
        "orm": _TestResultOrm,
        "derived": {"question_answers", "llm_assessment", "task", "candidate"},
    },
    {
        "domain": VacancyGraphSuggestion,
        "orm": VacancySuggestionOrm,
        "derived": {"vacancy", "parent_category", "parent_competency"},
    },
    {
        "domain": User,
        "orm": UserOrm,
    },
    {
        "domain": RefreshToken,
        "orm": RefreshTokenOrm,
        "derived": {"user", "is_expired"},
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
    derived_sources = {
        "Category.competencies": {"competencies", "sub_competencies"},
        "Competency.sub_competencies": {"sub_competencies"},
        "Vacancy.category_nodes": {"vacancy_category_nodes"},
        "Vacancy.competency_nodes": {"vacancy_competency_nodes"},
        "Vacancy.sub_competency_nodes": {"vacancy_sub_competency_nodes"},
        "Vacancy.suggestions": {"vacancy_graph_suggestions"},
        "Candidate.achieved_subcompetency_ids": {
            "candidate_sub_competency_achievements"
        },
        "Candidate.achievements": {"candidate_sub_competency_achievements"},
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
