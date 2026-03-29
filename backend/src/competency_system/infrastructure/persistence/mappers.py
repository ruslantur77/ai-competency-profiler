from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    RefreshToken,
    SubCompetency,
    Task,
    TaskCompetencyMapping,
    TestResult,
    User,
    Vacancy,
    VacancyGraphSuggestion,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    AssessmentStatus,
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    TaskType,
    VacancyStatus,
)
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CategoryOrm,
    CompetencyOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    TestResultOrm,
    UserOrm,
    VacancyOrm,
    VacancySuggestionOrm,
)


def _uuid_list_to_json(value: set[UUID] | list[UUID]) -> str:
    return json.dumps([str(item) for item in value], ensure_ascii=False)


def _json_to_uuid_set(value: str | None) -> set[UUID]:
    if not value:
        return set()
    return {UUID(item) for item in json.loads(value)}


def _json_loads(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    data = json.loads(value)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array")
    return data


def _serialize_subcompetency(subcompetency: SubCompetency) -> dict[str, Any]:
    return {
        "id": str(subcompetency.id),
        "name": subcompetency.name,
        "description": subcompetency.description,
        "target_level": int(subcompetency.target_level),
        "weight": subcompetency.weight,
        "created_at": subcompetency.created_at.isoformat(),
        "updated_at": subcompetency.updated_at.isoformat(),
    }


def _deserialize_subcompetency(data: dict[str, Any]) -> SubCompetency:
    return SubCompetency(
        id=UUID(str(data["id"])),
        name=str(data["name"]),
        description=str(data.get("description", "")),
        target_level=CompetencyLevel(int(data.get("target_level", 2))),
        weight=float(data.get("weight", 1.0)),
        created_at=datetime.fromisoformat(str(data["created_at"])),
        updated_at=datetime.fromisoformat(str(data["updated_at"])),
    )


def _serialize_competency(competency: Competency) -> dict[str, Any]:
    return {
        "id": str(competency.id),
        "category_id": str(competency.category_id),
        "name": competency.name,
        "description": competency.description,
        "is_required": competency.is_required,
        "sub_competencies": [
            _serialize_subcompetency(subcompetency)
            for subcompetency in competency.sub_competencies
        ],
        "created_at": competency.created_at.isoformat(),
        "updated_at": competency.updated_at.isoformat(),
    }


def _deserialize_competency(data: dict[str, Any]) -> Competency:
    return Competency(
        id=UUID(str(data["id"])),
        category_id=UUID(str(data["category_id"])),
        name=str(data["name"]),
        description=str(data.get("description", "")),
        is_required=bool(data.get("is_required", True)),
        sub_competencies=[
            _deserialize_subcompetency(item)
            for item in data.get("sub_competencies", [])
        ],
        created_at=datetime.fromisoformat(str(data["created_at"])),
        updated_at=datetime.fromisoformat(str(data["updated_at"])),
    )


def _serialize_category(category: Category) -> dict[str, Any]:
    return {
        "id": str(category.id),
        "name": category.name,
        "description": category.description,
        "emoji": category.emoji,
        "competencies": [
            _serialize_competency(competency) for competency in category.competencies
        ],
        "created_at": category.created_at.isoformat(),
        "updated_at": category.updated_at.isoformat(),
    }


def _deserialize_category(data: dict[str, Any]) -> Category:
    return Category(
        id=UUID(str(data["id"])),
        name=str(data["name"]),
        description=str(data.get("description", "")),
        emoji=str(data.get("emoji", "📋")),
        competencies=[
            _deserialize_competency(item) for item in data.get("competencies", [])
        ],
        created_at=datetime.fromisoformat(str(data["created_at"])),
        updated_at=datetime.fromisoformat(str(data["updated_at"])),
    )


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
    return Category(
        id=category.id,
        name=category.name,
        description=category.description,
        emoji=category.emoji,
        competencies=[
            competency_from_orm(competency) for competency in category.competencies
        ],
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def competency_to_orm(competency: Competency) -> CompetencyOrm:
    orm = CompetencyOrm(
        id=competency.id,
        category_id=competency.category_id,
        name=competency.name,
        description=competency.description,
        is_required=competency.is_required,
    )
    orm.sub_competencies = [
        subcompetency_to_orm(subcompetency, competency_id=competency.id)
        for subcompetency in competency.sub_competencies
    ]
    return orm


def competency_from_orm(competency: CompetencyOrm) -> Competency:
    return Competency(
        id=competency.id,
        category_id=competency.category_id,
        name=competency.name,
        description=competency.description,
        is_required=competency.is_required,
        sub_competencies=[
            subcompetency_from_orm(subcompetency)
            for subcompetency in competency.sub_competencies
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
        target_level=int(subcompetency.target_level),
        weight=subcompetency.weight,
    )


def subcompetency_from_orm(subcompetency: SubCompetencyOrm) -> SubCompetency:
    return SubCompetency(
        id=subcompetency.id,
        name=subcompetency.name,
        description=subcompetency.description,
        target_level=CompetencyLevel(int(subcompetency.target_level)),
        weight=subcompetency.weight,
        created_at=subcompetency.created_at,
        updated_at=subcompetency.updated_at,
    )


def vacancy_to_orm(vacancy: Vacancy) -> VacancyOrm:
    return VacancyOrm(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=vacancy.status.value,
        experience=vacancy.experience,
        key_skills=json.dumps(vacancy.key_skills, ensure_ascii=False),
        error_message=vacancy.error_message,
        categories_snapshot=json.dumps(
            [_serialize_category(category) for category in vacancy.categories],
            ensure_ascii=False,
        ),
        competencies_snapshot=json.dumps(
            [_serialize_competency(competency) for competency in vacancy.competencies],
            ensure_ascii=False,
        ),
    )


def vacancy_from_orm(vacancy: VacancyOrm) -> Vacancy:
    return Vacancy(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=VacancyStatus(vacancy.status),
        experience=vacancy.experience,
        key_skills=list(json.loads(vacancy.key_skills or "[]")),
        categories=[
            _deserialize_category(item)
            for item in _json_loads(vacancy.categories_snapshot)
        ],
        competencies=[
            _deserialize_competency(item)
            for item in _json_loads(vacancy.competencies_snapshot)
        ],
        error_message=vacancy.error_message,
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


def candidate_to_orm(candidate: Candidate) -> CandidateOrm:
    return CandidateOrm(
        id=candidate.id,
        external_id=candidate.external_id,
        status=candidate.assessment_status.value,
        achieved_subcompetency_ids=_uuid_list_to_json(
            candidate.achieved_subcompetency_ids
        ),
        last_assessment_at=candidate.last_assessment_at,
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
        expires_at=refresh_token.expires_at,
        revoked_at=refresh_token.revoked_at,
        created_at=refresh_token.created_at,
        updated_at=refresh_token.created_at,
    )


def candidate_from_orm(candidate: CandidateOrm) -> Candidate:
    return Candidate(
        id=candidate.id,
        external_id=candidate.external_id,
        achieved_subcompetency_ids=_json_to_uuid_set(
            candidate.achieved_subcompetency_ids
        ),
        assessment_status=AssessmentStatus(candidate.status),
        last_assessment_at=candidate.last_assessment_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def task_to_orm(task: Task) -> TaskOrm:
    return TaskOrm(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        description=task.description,
        type=task.type.value.lower(),
        mapping_validated=task.mapping_validated,
        competency_mappings=json.dumps(
            [
                {
                    "sub_competency_id": str(mapping.sub_competency_id),
                    "weight": mapping.weight,
                }
                for mapping in task.competency_mappings
            ],
            ensure_ascii=False,
        ),
    )


def task_from_orm(task: TaskOrm) -> Task:
    return Task(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        description=task.description,
        type=TaskType(str(task.type).lower()),
        competency_mappings=[
            TaskCompetencyMapping(
                sub_competency_id=UUID(str(mapping["sub_competency_id"])),
                weight=float(mapping.get("weight", 1.0)),
            )
            for mapping in _json_loads(task.competency_mappings)
        ],
        mapping_validated=task.mapping_validated,
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
        llm_assessment=json.dumps(test_result.llm_assessment, ensure_ascii=False)
        if test_result.llm_assessment is not None
        else None,
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
        llm_assessment=(
            json.loads(test_result.llm_assessment)
            if test_result.llm_assessment is not None
            else None
        ),
        created_at=test_result.created_at,
        updated_at=test_result.created_at,
    )


def vacancy_suggestion_to_orm(
    suggestion: VacancyGraphSuggestion,
) -> VacancySuggestionOrm:
    return VacancySuggestionOrm(
        id=suggestion.id,
        vacancy_id=suggestion.vacancy_id,
        stage=suggestion.stage.value,
        entity_type=suggestion.entity_type.value,
        status=suggestion.status.value,
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
        stage=SuggestionStage(suggestion.stage),
        entity_type=SuggestionEntityType(suggestion.entity_type),
        status=SuggestionStatus(suggestion.status),
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
