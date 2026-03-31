from __future__ import annotations

from sqlalchemy import inspect

from competency_system.infrastructure.persistence import models

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
    models.TaskSubCompetencyMappingOrm,
    models.TestResultQuestionAnswerOrm,
    models.TestResultLLMAssessmentOrm,
    models.TestResultLLMStrengthOrm,
    models.TestResultLLMIssueOrm,
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


def test_relationships_are_bidirectional_with_back_populates() -> None:
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
        models.TestResultLLMStrengthOrm,
        models.TestResultLLMIssueOrm,
        models.WebhookEventOrm,
        models.VacancySuggestionOrm,
        models.RankingSnapshotOrm,
    ]
    for orm_class in orm_classes:
        mapper = inspect(orm_class)
        for relation in mapper.relationships:
            assert relation.back_populates is not None, (
                f"{orm_class.__name__}.{relation.key} must declare back_populates"
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
