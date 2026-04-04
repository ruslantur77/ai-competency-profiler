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


def _load_all[T](
    model: Any, domain_model: type[T], seen: dict[int, Any] | None = None
) -> T:
    if seen is None:
        seen = {}
    obj_id = id(model)
    if obj_id in seen:
        return seen[obj_id]  # type: ignore

    seen[obj_id] = obj_id

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
                value = _load_all(value, field_type, seen)

            elif isinstance(value, list) and field_type:
                args = get_args(field_type)
                item_type = args[0] if args else None
                item_type = unwrap_type(item_type)

                if (
                    item_type
                    and is_dataclass(item_type)
                    and isinstance(item_type, type)
                ):
                    value = [_load_all(v, item_type, seen) for v in value]

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


def category_to_orm(
    category: Category,
    *,
    present_fields: Collection[str] | None = None,
) -> CategoryOrm:
    return CategoryOrm.from_entity(category, present_fields=present_fields)


def category_from_orm(category: CategoryOrm) -> Category:
    return _load_all(category, Category)


def competency_to_orm(
    competency: Competency,
    *,
    present_fields: Collection[str] | None = None,
) -> CompetencyOrm:
    return CompetencyOrm.from_entity(competency, present_fields=present_fields)


def competency_from_orm(competency: CompetencyOrm) -> Competency:
    return _load_all(competency, Competency)


def subcompetency_to_orm(
    subcompetency: SubCompetency,
    *,
    present_fields: Collection[str] | None = None,
) -> SubCompetencyOrm:
    return SubCompetencyOrm.from_entity(subcompetency, present_fields=present_fields)


def subcompetency_from_orm(subcompetency: SubCompetencyOrm) -> SubCompetency:
    return _load_all(subcompetency, SubCompetency)


def vacancy_to_orm(
    vacancy: Vacancy,
    *,
    present_fields: Collection[str] | None = None,
) -> VacancyOrm:
    return VacancyOrm.from_entity(vacancy, present_fields=present_fields)


def vacancy_from_orm(vacancy: VacancyOrm) -> Vacancy:
    return _load_all(vacancy, Vacancy)


def vacancy_category_node_to_orm(
    node: VacancyCategoryNode,
    *,
    present_fields: Collection[str] | None = None,
) -> VacancyCategoryNodeOrm:
    return VacancyCategoryNodeOrm.from_entity(node, present_fields=present_fields)


def vacancy_category_node_from_orm(node: VacancyCategoryNodeOrm) -> VacancyCategoryNode:
    return _load_all(node, VacancyCategoryNode)


def vacancy_competency_node_to_orm(
    node: VacancyCompetencyNode,
    *,
    present_fields: Collection[str] | None = None,
) -> VacancyCompetencyNodeOrm:
    return VacancyCompetencyNodeOrm.from_entity(node, present_fields=present_fields)


def vacancy_competency_node_from_orm(
    node: VacancyCompetencyNodeOrm,
) -> VacancyCompetencyNode:
    return _load_all(node, VacancyCompetencyNode)


def vacancy_sub_competency_node_to_orm(
    node: VacancySubCompetencyNode,
    *,
    present_fields: Collection[str] | None = None,
) -> VacancySubCompetencyNodeOrm:
    return VacancySubCompetencyNodeOrm.from_entity(node, present_fields=present_fields)


def vacancy_sub_competency_node_from_orm(
    node: VacancySubCompetencyNodeOrm,
) -> VacancySubCompetencyNode:
    return _load_all(node, VacancySubCompetencyNode)


def candidate_to_orm(
    candidate: Candidate,
    *,
    present_fields: Collection[str] | None = None,
) -> CandidateOrm:
    return CandidateOrm.from_entity(candidate, present_fields=present_fields)


def candidate_from_orm(candidate: CandidateOrm) -> Candidate:
    return _load_all(candidate, Candidate)


def user_to_orm(
    user: User,
    *,
    present_fields: Collection[str] | None = None,
) -> UserOrm:
    return UserOrm.from_entity(user, present_fields=present_fields)


def user_from_orm(user: UserOrm) -> User:
    return _load_all(user, User)


def refresh_token_to_orm(
    refresh_token: RefreshToken,
    *,
    present_fields: Collection[str] | None = None,
) -> RefreshTokenOrm:
    return RefreshTokenOrm.from_entity(refresh_token, present_fields=present_fields)


def refresh_token_from_orm(refresh_token: RefreshTokenOrm) -> RefreshToken:
    return _load_all(refresh_token, RefreshToken)


def task_to_orm(
    task: Task,
    *,
    present_fields: Collection[str] | None = None,
) -> TaskOrm:
    return TaskOrm.from_entity(task, present_fields=present_fields)


def task_from_orm(task: TaskOrm) -> Task:
    return _load_all(task, Task)


def test_result_to_orm(
    test_result: TestResult,
    *,
    present_fields: Collection[str] | None = None,
) -> TestResultOrm:
    return TestResultOrm.from_entity(test_result, present_fields=present_fields)


def test_result_from_orm(test_result: TestResultOrm) -> TestResult:
    return _load_all(test_result, TestResult)


def webhook_event_to_orm(
    event: WebhookEvent,
    *,
    present_fields: Collection[str] | None = None,
) -> WebhookEventOrm:
    return WebhookEventOrm.from_entity(event, present_fields=present_fields)


def webhook_event_from_orm(event: WebhookEventOrm) -> WebhookEvent:
    return _load_all(event, WebhookEvent)


def ranking_snapshot_to_orm(
    snapshot: RankingSnapshot,
    *,
    present_fields: Collection[str] | None = None,
) -> RankingSnapshotOrm:
    return RankingSnapshotOrm.from_entity(snapshot, present_fields=present_fields)


def ranking_snapshot_from_orm(snapshot: RankingSnapshotOrm) -> RankingSnapshot:
    return _load_all(snapshot, RankingSnapshot)


def vacancy_suggestion_to_orm(
    suggestion: VacancyGraphSuggestion,
    *,
    present_fields: Collection[str] | None = None,
) -> VacancySuggestionOrm:
    return VacancySuggestionOrm.from_entity(suggestion, present_fields=present_fields)


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
