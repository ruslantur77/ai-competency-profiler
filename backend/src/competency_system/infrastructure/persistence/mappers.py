from __future__ import annotations

import types
import typing
from collections.abc import Collection
from dataclasses import is_dataclass
from datetime import UTC, datetime
from typing import Any, get_args, get_type_hints

from sqlalchemy import inspect as sa_inspect

import competency_system.domain.entities as _e_module
from competency_system.application.dtos.webhooks import RankingSnapshot, WebhookEvent
from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    RefreshToken,
    SubCompetency,
    Task,
    TestResult,
    TestResultLLMAssessment,
    TestResultQuestionAnswer,
    User,
    Vacancy,
    VacancyCategoryNode,
    VacancyCompetencyNode,
    VacancyGraphSuggestion,
    VacancySubCompetencyNode,
)
from competency_system.infrastructure.logging import get_logger
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CategoryOrm,
    CompetencyOrm,
    RankingSnapshotOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    TestResultLLMAssessmentOrm,
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
        return args[0] if len(args) == 1 else typing.Union[tuple(args)]  # noqa: UP007
    return field_type


def normalize_include[T](include: Collection[T] | None) -> frozenset[T]:
    return frozenset(include or ())


logger = get_logger(__name__)


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


def category_from_orm(category: CategoryOrm) -> Category:
    return _load_all(category, Category)


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


def competency_from_orm(competency: CompetencyOrm) -> Competency:
    return _load_all(competency, Competency)


def subcompetency_to_orm(subcompetency: SubCompetency) -> SubCompetencyOrm:
    return SubCompetencyOrm(
        id=subcompetency.id,
        competency_id=subcompetency.competency_id,
        name=subcompetency.name,
        description=subcompetency.description,
        weight=subcompetency.weight,
    )


def subcompetency_from_orm(subcompetency: SubCompetencyOrm) -> SubCompetency:
    return _load_all(subcompetency, SubCompetency)


def vacancy_to_orm(vacancy: Vacancy) -> VacancyOrm:
    return VacancyOrm(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=vacancy.status,
        error_message=vacancy.error_message,
    )


def vacancy_from_orm(vacancy: VacancyOrm) -> Vacancy:
    return _load_all(vacancy, Vacancy)


def vacancy_category_node_to_orm(node: VacancyCategoryNode) -> VacancyCategoryNodeOrm:
    return VacancyCategoryNodeOrm(
        id=node.id,
        vacancy_id=node.vacancy_id,
        category_id=node.category_id,
        position=node.position,
    )


def vacancy_category_node_from_orm(node: VacancyCategoryNodeOrm) -> VacancyCategoryNode:
    return _load_all(node, VacancyCategoryNode)


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
    node: VacancyCompetencyNodeOrm,
) -> VacancyCompetencyNode:
    return _load_all(node, VacancyCompetencyNode)


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
    node: VacancySubCompetencyNodeOrm,
) -> VacancySubCompetencyNode:
    return _load_all(node, VacancySubCompetencyNode)


def candidate_to_orm(candidate: Candidate) -> CandidateOrm:
    return CandidateOrm(
        id=candidate.id,
        external_id=candidate.external_id,
        vacancy_id=candidate.vacancy_id,
        status=candidate.status,
        last_assessment_at=candidate.last_assessment_at,
    )


def candidate_from_orm(candidate: CandidateOrm) -> Candidate:
    return _load_all(candidate, Candidate)


def user_to_orm(user: User) -> UserOrm:
    return UserOrm(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


def user_from_orm(user: UserOrm) -> User:
    return _load_all(user, User)


def refresh_token_to_orm(refresh_token: RefreshToken) -> RefreshTokenOrm:
    return RefreshTokenOrm(
        jti=refresh_token.jti,
        user_id=refresh_token.user_id,
        token_hash=refresh_token.token_hash,
        expires_at=refresh_token.expires_at,
        revoked_at=refresh_token.revoked_at,
        created_at=refresh_token.created_at,
    )


def refresh_token_from_orm(refresh_token: RefreshTokenOrm) -> RefreshToken:
    return _load_all(refresh_token, RefreshToken)


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


def task_from_orm(task: TaskOrm) -> Task:
    return _load_all(task, Task)


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


def test_result_from_orm(test_result: TestResultOrm) -> TestResult:
    return _load_all(test_result, TestResult)


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


def webhook_event_from_orm(event: WebhookEventOrm) -> WebhookEvent:
    return _load_all(event, WebhookEvent)


def ranking_snapshot_to_orm(snapshot: RankingSnapshot) -> RankingSnapshotOrm:
    return RankingSnapshotOrm(
        id=snapshot.id,
        vacancy_id=snapshot.vacancy_id,
        payload=snapshot.payload.data,
        calculated_at=snapshot.calculated_at,
    )


def ranking_snapshot_from_orm(snapshot: RankingSnapshotOrm) -> RankingSnapshot:
    return _load_all(snapshot, RankingSnapshot)


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
    suggestion: VacancySuggestionOrm,
) -> VacancyGraphSuggestion:
    return _load_all(suggestion, VacancyGraphSuggestion)


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
    return _load_all(assessment, TestResultLLMAssessment)
