from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.attributes import NO_VALUE

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
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import TaskType
from competency_system.infrastructure.persistence.models import (
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


def _loaded_relation(model: object, attr_name: str) -> list[object]:
    state = sa_inspect(model)
    loaded = state.attrs[attr_name].loaded_value
    if loaded is NO_VALUE:
        return []
    return list(loaded)


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
    competencies = _loaded_relation(category, "competencies")
    return Category(
        id=category.id,
        name=category.name,
        description=category.description,
        emoji=category.emoji,
        competencies=[competency_from_orm(competency) for competency in competencies],
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def competency_to_orm(competency: Competency) -> CompetencyOrm:
    orm = CompetencyOrm(
        id=competency.id,
        category_id=competency.category_id,
        name=competency.name,
        description=competency.description,
    )
    orm.sub_competencies = [
        subcompetency_to_orm(subcompetency, competency_id=competency.id)
        for subcompetency in competency.sub_competencies
    ]
    return orm


def competency_from_orm(competency: CompetencyOrm) -> Competency:
    sub_competencies = _loaded_relation(competency, "sub_competencies")
    return Competency(
        id=competency.id,
        category_id=competency.category_id,
        name=competency.name,
        description=competency.description,
        sub_competencies=[
            subcompetency_from_orm(subcompetency) for subcompetency in sub_competencies
        ],
        created_at=competency.created_at,
        updated_at=competency.updated_at,
    )


def subcompetency_to_orm(
    subcompetency: SubCompetency,
    *,
    competency_id: UUID | None = None,
) -> SubCompetencyOrm:
    return SubCompetencyOrm(
        id=subcompetency.id,
        competency_id=competency_id or UUID(int=0),
        name=subcompetency.name,
        description=subcompetency.description,
    )


def subcompetency_from_orm(subcompetency: SubCompetencyOrm) -> SubCompetency:
    return SubCompetency(
        id=subcompetency.id,
        name=subcompetency.name,
        description=subcompetency.description,
        target_level=CompetencyLevel.BEGINNER,
        weight=1.0,
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


def vacancy_from_orm(vacancy: VacancyOrm) -> Vacancy:
    return Vacancy(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=vacancy.status,
        categories=[],
        competencies=[],
        error_message=vacancy.error_message,
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


def candidate_to_orm(candidate: Candidate) -> CandidateOrm:
    return CandidateOrm(
        id=candidate.id,
        external_id=candidate.external_id,
        vacancy_id=candidate.vacancy_id,
        status=candidate.assessment_status,
        last_assessment_at=candidate.last_assessment_at,
    )


def candidate_from_orm(candidate: CandidateOrm) -> Candidate:
    return Candidate(
        id=candidate.id,
        external_id=candidate.external_id,
        vacancy_id=candidate.vacancy_id,
        achieved_subcompetency_ids=set(),
        assessment_status=candidate.status,
        last_assessment_at=candidate.last_assessment_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def user_to_orm(user: User) -> UserOrm:
    return UserOrm(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        role=user.role,
        is_active=user.is_active,
    )


def user_from_orm(user: UserOrm) -> User:
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


def refresh_token_from_orm(refresh_token: RefreshTokenOrm) -> RefreshToken:
    return RefreshToken(
        id=refresh_token.jti,
        jti=refresh_token.jti,
        user_id=refresh_token.user_id,
        token_hash=refresh_token.token_hash,
        expires_at=_normalize_utc(refresh_token.expires_at) or refresh_token.expires_at,
        revoked_at=_normalize_utc(refresh_token.revoked_at),
        created_at=_normalize_utc(refresh_token.created_at) or refresh_token.created_at,
        updated_at=_normalize_utc(refresh_token.created_at) or refresh_token.created_at,
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


def task_from_orm(task: TaskOrm) -> Task:
    return Task(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        description=task.description,
        type=TaskType(task.type),
        competency_mappings=[],
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


def test_result_from_orm(test_result: TestResultOrm) -> TestResult:
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
        payload=event.payload or {},
        processed_at=event.processed_at,
    )


def webhook_event_from_orm(event: WebhookEventOrm) -> WebhookEvent:
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
        payload=dict(event.payload or {}),
        processed_at=event.processed_at,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def ranking_snapshot_to_orm(snapshot: RankingSnapshot) -> RankingSnapshotOrm:
    return RankingSnapshotOrm(
        id=snapshot.id,
        vacancy_id=snapshot.vacancy_id,
        payload=snapshot.payload,
        calculated_at=snapshot.calculated_at,
    )


def ranking_snapshot_from_orm(snapshot: RankingSnapshotOrm) -> RankingSnapshot:
    return RankingSnapshot(
        id=snapshot.id,
        vacancy_id=snapshot.vacancy_id,
        payload=dict(snapshot.payload or {}),
        calculated_at=snapshot.calculated_at,
        created_at=snapshot.calculated_at,
        updated_at=snapshot.calculated_at,
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
    suggestion: VacancySuggestionOrm,
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
