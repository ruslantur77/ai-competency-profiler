from __future__ import annotations

import pytest
from sqlalchemy import inspect

from competency_system.infrastructure.persistence import models

pytestmark = pytest.mark.contract

ORM_CLASSES_WITH_FK = [
    models.RefreshTokenOrm,
    models.CompetencyOrm,
    models.SubCompetencyOrm,
    models.VacancyCategoryNodeOrm,
    models.VacancyCompetencyNodeOrm,
    models.VacancySubCompetencyNodeOrm,
    models.VacancySuggestionOrm,
    models.CandidateOrm,
    models.CandidateSubCompetencyAchievementOrm,
    models.TestResultOrm,
    models.TaskCategoryNodeOrm,
    models.TaskCompetencyNodeOrm,
    models.TaskSubCompetencyNodeOrm,
    models.TestResultQuestionAnswerOrm,
    models.TestResultLLMAssessmentOrm,
    models.TestResultLLMFeedbackOrm,
    models.WebhookEventOrm,
    models.RankingSnapshotOrm,
]


def test_each_fk_column_has_owner_relationship() -> None:
    for orm_class in ORM_CLASSES_WITH_FK:
        mapper = inspect(orm_class)
        fk_column_names = {
            fk.parent.name
            for column in orm_class.__table__.columns
            for fk in column.foreign_keys
        }
        owner_side_columns = {
            column.name
            for relation in mapper.relationships
            for column in relation.local_columns
        }
        assert fk_column_names <= owner_side_columns, (
            f"{orm_class.__name__} has FK columns without relationships: "
            f"{sorted(fk_column_names - owner_side_columns)}"
        )


def test_back_populates_pairs_are_bidirectional() -> None:
    orm_classes = [
        models.UserOrm,
        models.CategoryOrm,
        models.CompetencyOrm,
        models.SubCompetencyOrm,
        models.VacancyOrm,
        models.CandidateOrm,
        models.TaskOrm,
        models.TestResultOrm,
        models.TestResultQuestionAnswerOrm,
        models.TestResultLLMAssessmentOrm,
        models.TestResultLLMFeedbackOrm,
        models.WebhookEventOrm,
        models.VacancySuggestionOrm,
        models.RankingSnapshotOrm,
        models.RefreshTokenOrm,
        models.VacancyCategoryNodeOrm,
        models.VacancyCompetencyNodeOrm,
        models.VacancySubCompetencyNodeOrm,
    ]
    for orm_class in orm_classes:
        mapper = inspect(orm_class)
        for relation in mapper.relationships:
            if relation.back_populates is None:
                continue
            related_mapper = relation.mapper
            assert relation.back_populates in related_mapper.relationships, (
                f"{orm_class.__name__}.{relation.key} back_populates points "
                f"to missing relation {related_mapper.class_.__name__}."
                f"{relation.back_populates}"
            )


def test_expected_one_to_one_relationships_are_scalar() -> None:
    vacancy_relationships = inspect(models.VacancyOrm).relationships
    ranking_relationships = inspect(models.RankingSnapshotOrm).relationships
    test_result_relationships = inspect(models.TestResultOrm).relationships
    llm_relationships = inspect(models.TestResultLLMAssessmentOrm).relationships

    assert vacancy_relationships["ranking_snapshot"].uselist is False
    assert ranking_relationships["vacancy"].uselist is False
    assert test_result_relationships["llm_assessment"].uselist is False
    assert llm_relationships["test_result"].uselist is False
