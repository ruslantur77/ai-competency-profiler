from __future__ import annotations

import types
import typing
from collections.abc import Collection
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from typing import Any, List, TypeVar, Union, cast, get_args, get_origin, get_type_hints

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.orm.attributes import NO_VALUE

import competency_system.domain.entities as _e_module
from competency_system.application.ports.repositories import (
    CandidateInclude,
    CategoryInclude,
    CompetencyInclude,
    TaskInclude,
    TestResultInclude,
    VacancyInclude,
)
from competency_system.domain.entities import (
    Candidate,
    CandidateSubCompetencyAchievement,
    Category,
    Competency,
    RefreshToken,
    SubCompetency,
    Task,
    TaskSubCompetencyMapping,
    TestResult,
    TestResultLLMAssessment,
    TestResultLLMFeedbackItem,
    TestResultQuestionAnswer,
    User,
    Vacancy,
    VacancyCategoryNode,
    VacancyCompetencyNode,
    VacancyGraphSuggestion,
    VacancySubCompetencyNode,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.infrastructure.logging import get_logger
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CandidateSubCompetencyAchievementOrm,
    CategoryOrm,
    CompetencyOrm,
    RankingSnapshotOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    TaskSubCompetencyMappingOrm,
    TestResultLLMAssessmentOrm,
    TestResultLLMFeedbackOrm,
    TestResultOrm,
    TestResultQuestionAnswerOrm,
    UserOrm,
    VacancyCategoryNodeOrm,
    VacancyCompetencyNodeOrm,
    VacancyOrm,
    VacancySubCompetencyNodeOrm,
    VacancySuggestionOrm,
    WebhookEventOrm,
)


def unwrap_type(field_type: Any) -> Any:
    origin = typing.get_origin(field_type)
    if origin is typing.Union or isinstance(field_type, types.UnionType):
        args = [a for a in typing.get_args(field_type) if a is not type(None)]
        return args[0] if len(args) == 1 else typing.Union[tuple(args)]
    return field_type


# from competency_system.infrastructure.persistence.repositories.base import (
#     normalize_include,
# )
def normalize_include[T](include: Collection[T] | None) -> frozenset[T]:
    return frozenset(include or ())


logger = get_logger(__name__)


def _loaded_relation_list[T](
    model: object,
    attr: InstrumentedAttribute[list[T]],
) -> list[T]:
    state = sa_inspect(model)
    if not state:
        return []

    loaded = state.attrs[attr.key].loaded_value

    if loaded is NO_VALUE:
        return []

    return list(loaded)


def _loaded_relation_entity[T](
    model: object,
    attr: InstrumentedAttribute[T],
) -> T | None:
    state = sa_inspect(model)
    if not state:
        return None

    loaded = state.attrs[attr.key].loaded_value

    if loaded is NO_VALUE:
        return None

    return loaded


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _load_all[T](model: Any, domain_model: type[T]) -> T:
    if not hasattr(model, "__mapper__"):
        raise ValueError("only orm models can be used here")
    if not is_dataclass(domain_model):
        raise TypeError("domain_model must be a dataclass")

    hints = get_type_hints(domain_model, localns={**vars(_e_module)})
    insp = sa_inspect(model)
    data = {}

    for name in insp.attrs.keys():  # noqa: SIM118
        if name in insp.unloaded or name not in insp.dict:
            continue
        value = None
        try:
            value = getattr(model, name)
            field_type = hints.get(name)
            field_type = unwrap_type(field_type)

            if (
                hasattr(value, "__mapper__")
                and field_type
                and is_dataclass(field_type)
                and isinstance(field_type, type)
            ):
                value = _load_all(value, field_type)

            elif isinstance(value, list) and field_type:
                args = get_args(field_type)
                item_type = args[0] if args else None
                item_type = unwrap_type(item_type)

                if (
                    item_type
                    and is_dataclass(item_type)
                    and isinstance(item_type, type)
                ):
                    value = [_load_all(v, item_type) for v in value]

            elif isinstance(value, datetime):
                value = _normalize_utc(value)

            data[name] = value
        except Exception:
            logger.warning(
                f"Error convert orm {type(model)} field {name}"
                + f" with value {value} to domain model"
            )
            continue

    return domain_model(**data)


def category_to_orm(category: Category) -> CategoryOrm:
    orm = CategoryOrm(
        id=category.id,
        name=category.name,
        description=category.description,
        emoji=category.emoji,
    )
    orm.competencies = [
        competency_to_orm(competency) for competency in category.competencies
    ]
    return orm


def category_from_orm(
    category: CategoryOrm, include: Collection[CategoryInclude] | None = None
) -> Category:
    category_domain = Category(
        id=category.id,
        name=category.name,
        description=category.description,
        emoji=category.emoji,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )
    if include and CategoryInclude.COMPETENCIES in include:
        competencies = _loaded_relation_list(category, CategoryOrm.competencies)
        category_domain.competencies = [
            competency_from_orm(
                competency,
                include={CompetencyInclude.SUB_COMPETENCIES}
                if CategoryInclude.SUB_COMPETENCIES in include
                else None,
            )
            for competency in competencies
        ]

    return category_domain


def competency_to_orm(competency: Competency) -> CompetencyOrm:
    orm = CompetencyOrm(
        id=competency.id,
        category_id=competency.category_id,
        name=competency.name,
        description=competency.description,
    )
    orm.sub_competencies = [
        subcompetency_to_orm(subcompetency)
        for subcompetency in competency.sub_competencies
    ]
    return orm


def competency_from_orm(
    competency: CompetencyOrm, include: Collection[CompetencyInclude] | None = None
) -> Competency:
    competency_domain = Competency(
        id=competency.id,
        category_id=competency.category_id,
        name=competency.name,
        description=competency.description,
        created_at=competency.created_at,
        updated_at=competency.updated_at,
    )
    if include:
        if CompetencyInclude.SUB_COMPETENCIES in include:
            sub_competencies = _loaded_relation_list(
                competency, CompetencyOrm.sub_competencies
            )
            competency_domain.sub_competencies = [
                subcompetency_from_orm(subcompetency)
                for subcompetency in sub_competencies
            ]
        if CompetencyInclude.CATEGORY in include:
            category = _loaded_relation_entity(competency, CompetencyOrm.category)
            if category is not None:
                competency_domain.category = category_from_orm(category)

    return competency_domain


def subcompetency_to_orm(subcompetency: SubCompetency) -> SubCompetencyOrm:
    return SubCompetencyOrm(
        id=subcompetency.id,
        competency_id=subcompetency.competency_id,
        name=subcompetency.name,
        description=subcompetency.description,
    )


def subcompetency_from_orm(
    subcompetency: SubCompetencyOrm, include: None = None
) -> SubCompetency:
    return SubCompetency(
        id=subcompetency.id,
        competency_id=subcompetency.competency_id,
        name=subcompetency.name,
        description=subcompetency.description,
        created_at=subcompetency.created_at,
        updated_at=subcompetency.updated_at,
    )


def vacancy_to_orm(vacancy: Vacancy) -> VacancyOrm:
    return VacancyOrm(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=vacancy.status,
        error_message=vacancy.error_message,
    )


def vacancy_from_orm(
    vacancy: VacancyOrm, include: Collection[VacancyInclude] | None = None
) -> Vacancy:
    return Vacancy(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=vacancy.status,
        error_message=vacancy.error_message,
        category_nodes=[],
        competency_nodes=[],
        sub_competency_nodes=[],
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


def vacancy_category_node_to_orm(node: VacancyCategoryNode) -> VacancyCategoryNodeOrm:
    return VacancyCategoryNodeOrm(
        id=node.id,
        vacancy_id=node.vacancy_id,
        category_id=node.category_id,
        position=node.position,
    )


def vacancy_category_node_from_orm(
    node: VacancyCategoryNodeOrm, include: None = None
) -> VacancyCategoryNode:
    return VacancyCategoryNode(
        id=node.id,
        vacancy_id=node.vacancy_id,
        category_id=node.category_id,
        position=node.position,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def vacancy_competency_node_to_orm(
    node: VacancyCompetencyNode,
) -> VacancyCompetencyNodeOrm:
    return VacancyCompetencyNodeOrm(
        id=node.id,
        vacancy_id=node.vacancy_id,
        competency_id=node.competency_id,
        category_id=node.category_id,
        is_required=node.is_required,
        position=node.position,
    )


def vacancy_competency_node_from_orm(
    node: VacancyCompetencyNodeOrm, include: None = None
) -> VacancyCompetencyNode:
    return VacancyCompetencyNode(
        id=node.id,
        vacancy_id=node.vacancy_id,
        competency_id=node.competency_id,
        category_id=node.category_id,
        is_required=node.is_required,
        position=node.position,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def vacancy_sub_competency_node_to_orm(
    node: VacancySubCompetencyNode,
) -> VacancySubCompetencyNodeOrm:
    return VacancySubCompetencyNodeOrm(
        id=node.id,
        vacancy_id=node.vacancy_id,
        sub_competency_id=node.sub_competency_id,
        competency_id=node.competency_id,
        target_level=int(node.target_level),
        weight=node.weight,
        position=node.position,
    )


def vacancy_sub_competency_node_from_orm(
    node: VacancySubCompetencyNodeOrm, include: None = None
) -> VacancySubCompetencyNode:
    return VacancySubCompetencyNode(
        id=node.id,
        vacancy_id=node.vacancy_id,
        sub_competency_id=node.sub_competency_id,
        competency_id=node.competency_id,
        target_level=CompetencyLevel(node.target_level),
        weight=node.weight,
        position=node.position,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def candidate_to_orm(candidate: Candidate) -> CandidateOrm:
    return CandidateOrm(
        id=candidate.id,
        external_id=candidate.external_id,
        vacancy_id=candidate.vacancy_id,
        status=candidate.status,
        last_assessment_at=candidate.last_assessment_at,
    )


def candidate_from_orm(
    candidate: CandidateOrm, include: Collection[CandidateInclude] | None = None
) -> Candidate:
    candidate_domain = Candidate(
        id=candidate.id,
        external_id=candidate.external_id,
        vacancy_id=candidate.vacancy_id,
        status=candidate.status,
        last_assessment_at=candidate.last_assessment_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )
    if not include:
        return candidate_domain

    includes = normalize_include(include)
    if CandidateInclude.ACHIEVEMENTS in includes:
        achievements = _loaded_relation_list(candidate, CandidateOrm.achievements)
        candidate_domain.achievements = [
            CandidateSubCompetencyAchievement(
                id=row.id,
                candidate_id=row.candidate_id,
                sub_competency_id=row.sub_competency_id,
                achieved_at=row.achieved_at,
                created_at=row.achieved_at,
                updated_at=row.achieved_at,
            )
            for row in achievements
        ]
    if CandidateInclude.TEST_RESULTS in includes:
        test_results = _loaded_relation_list(candidate, CandidateOrm.test_results)
        candidate_domain.test_results = [
            test_result_from_orm(row) for row in test_results
        ]
    if CandidateInclude.VACANCY in includes:
        vacancy = _loaded_relation_entity(candidate, CandidateOrm.vacancy)
        if vacancy:
            candidate_domain.vacancy = vacancy_from_orm(vacancy)

    return candidate_domain


def user_to_orm(user: User) -> UserOrm:
    return UserOrm(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        role=user.role,
        is_active=user.is_active,
    )


def user_from_orm(user: UserOrm, include: None = None) -> User:
    return User(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def refresh_token_to_orm(refresh_token: RefreshToken) -> RefreshTokenOrm:
    return RefreshTokenOrm(
        jti=refresh_token.jti,
        user_id=refresh_token.user_id,
        token_hash=refresh_token.token_hash,
        expires_at=refresh_token.expires_at,
        revoked_at=refresh_token.revoked_at,
        created_at=refresh_token.created_at,
    )


def refresh_token_from_orm(
    refresh_token: RefreshTokenOrm, include: None = None
) -> RefreshToken:
    return RefreshToken(
        jti=refresh_token.jti,
        user_id=refresh_token.user_id,
        token_hash=refresh_token.token_hash,
        expires_at=_normalize_utc(refresh_token.expires_at) or refresh_token.expires_at,
        revoked_at=_normalize_utc(refresh_token.revoked_at),
        created_at=_normalize_utc(refresh_token.created_at) or refresh_token.created_at,
    )


def task_to_orm(task: Task) -> TaskOrm:
    return TaskOrm(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        description=task.description,
        type=task.type,
        mapping_validated=task.mapping_validated,
        mapping_status=task.mapping_status,
        mapping_error_message=task.mapping_error_message,
    )


def task_from_orm(
    task: TaskOrm, include: Collection[TaskInclude] | None = None
) -> Task:
    mappings = _loaded_relation_list(task, "sub_competency_mappings")
    return Task(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        description=task.description,
        type=task.type,
        sub_competency_mappings=[
            TaskSubCompetencyMapping(
                id=row.id,
                task_id=row.task_id,
                sub_competency_id=row.sub_competency_id,
                weight=row.weight,
                position=row.position,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            for row in sorted(mappings, key=lambda item: item.position)
        ],
        mapping_validated=task.mapping_validated,
        mapping_status=task.mapping_status,
        mapping_error_message=task.mapping_error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def test_result_to_orm(test_result: TestResult) -> TestResultOrm:
    return TestResultOrm(
        id=test_result.id,
        candidate_id=test_result.candidate_id,
        task_id=test_result.task_id,
        passed=test_result.passed,
        score=test_result.score,
        attempts=test_result.attempts,
        code_submitted=test_result.code_submitted,
    )


def test_result_from_orm(
    test_result: TestResultOrm, include: Collection[TestResultInclude] | None = None
) -> TestResult:
    return TestResult(
        id=test_result.id,
        candidate_id=test_result.candidate_id,
        task_id=test_result.task_id,
        passed=test_result.passed,
        score=test_result.score,
        attempts=test_result.attempts,
        code_submitted=test_result.code_submitted,
        question_answers=[],
        llm_assessment=None,
        created_at=test_result.created_at,
        updated_at=test_result.created_at,
    )


def webhook_event_to_orm(event: WebhookEvent) -> WebhookEventOrm:
    return WebhookEventOrm(
        id=event.id,
        event_id=event.event_id,
        vacancy_id=event.vacancy_id,
        candidate_external_id=event.candidate_external_id,
        task_external_id=event.task_external_id,
        status=event.status,
        error_message=event.error_message,
        candidate_id=event.candidate_id,
        test_result_id=event.test_result_id,
        payload=event.payload.data,
        processed_at=event.processed_at,
    )


def webhook_event_from_orm(
    event: WebhookEventOrm, include: None = None
) -> WebhookEvent:
    return WebhookEvent(
        id=event.id,
        event_id=event.event_id,
        vacancy_id=event.vacancy_id,
        candidate_external_id=event.candidate_external_id,
        task_external_id=event.task_external_id,
        status=event.status,
        error_message=event.error_message,
        candidate_id=event.candidate_id,
        test_result_id=event.test_result_id,
        payload=WebhookEventPayload(data=dict(event.payload or {})),
        processed_at=event.processed_at,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def ranking_snapshot_to_orm(snapshot: RankingSnapshot) -> RankingSnapshotOrm:
    return RankingSnapshotOrm(
        id=snapshot.id,
        vacancy_id=snapshot.vacancy_id,
        payload=snapshot.payload.data,
        calculated_at=snapshot.calculated_at,
    )


def ranking_snapshot_from_orm(
    snapshot: RankingSnapshotOrm, include: None = None
) -> RankingSnapshot:
    return RankingSnapshot(
        id=snapshot.id,
        vacancy_id=snapshot.vacancy_id,
        payload=RankingSnapshotPayload(data=dict(snapshot.payload or {})),
        calculated_at=snapshot.calculated_at,
        created_at=snapshot.calculated_at,
    )


def vacancy_suggestion_to_orm(
    suggestion: VacancyGraphSuggestion,
) -> VacancySuggestionOrm:
    return VacancySuggestionOrm(
        id=suggestion.id,
        vacancy_id=suggestion.vacancy_id,
        stage=suggestion.stage,
        entity_type=suggestion.entity_type,
        status=suggestion.status,
        name=suggestion.name,
        description=suggestion.description,
        reason=suggestion.reason,
        parent_category_id=suggestion.parent_category_id,
        parent_competency_id=suggestion.parent_competency_id,
        is_required=suggestion.is_required,
        target_level=(
            int(suggestion.target_level)
            if suggestion.target_level is not None
            else None
        ),
        weight=suggestion.weight,
    )


def vacancy_suggestion_from_orm(
    suggestion: VacancySuggestionOrm, include: None = None
) -> VacancyGraphSuggestion:
    return VacancyGraphSuggestion(
        id=suggestion.id,
        vacancy_id=suggestion.vacancy_id,
        stage=suggestion.stage,
        entity_type=suggestion.entity_type,
        status=suggestion.status,
        name=suggestion.name,
        description=suggestion.description,
        reason=suggestion.reason,
        parent_category_id=suggestion.parent_category_id,
        parent_competency_id=suggestion.parent_competency_id,
        is_required=suggestion.is_required,
        target_level=(
            CompetencyLevel(suggestion.target_level)
            if suggestion.target_level is not None
            else None
        ),
        weight=suggestion.weight,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


def test_result_question_answer_from_orm(
    row: TestResultQuestionAnswerOrm,
) -> TestResultQuestionAnswer:
    return TestResultQuestionAnswer(
        id=row.id,
        test_result_id=row.test_result_id,
        question=row.question,
        answer=row.answer,
        position=row.position,
    )


def test_result_llm_assessment_from_orm(
    assessment: TestResultLLMAssessmentOrm,
) -> TestResultLLMAssessment:
    return TestResultLLMAssessment(
        id=assessment.id,
        test_result_id=assessment.test_result_id,
        passed=assessment.passed,
        score=assessment.score,
        feedback=assessment.feedback,
        criteria_version=assessment.criteria_version,
        raw_test_score=assessment.raw_test_score,
        penalized_test_score=assessment.penalized_test_score,
        attempt_penalty_applied=assessment.attempt_penalty_applied,
        final_score=assessment.final_score,
        feedback_items=[
            TestResultLLMFeedbackItem(
                id=row.id,
                assessment_id=row.assessment_id,
                type=row.type,
                value=row.value,
                position=row.position,
            )
            for row in assessment.feedback_items
        ],
    )
