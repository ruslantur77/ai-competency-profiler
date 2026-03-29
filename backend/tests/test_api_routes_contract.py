from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from competency_system.application.dtos.auth import (
    CurrentUserDTO,
    RefreshTokenDataDTO,
    TokenPairDTO,
)
from competency_system.application.dtos.candidate import (
    CandidateAssessmentResultDTO,
    CandidateProfileDTO,
    CompetencyScoreDTO,
)
from competency_system.application.dtos.competency import (
    CategoryDTO,
    CompetencyDTO,
    SubCompetencyDTO,
)
from competency_system.application.dtos.ranking import (
    RankingBreakdownItemDTO,
    RankingItemDTO,
    VacancyRankingDTO,
)
from competency_system.application.dtos.task import (
    SyncTasksResultDTO,
    TaskCompetencyMappingDTO,
    TaskDTO,
    TestResultDTO,
)
from competency_system.application.dtos.vacancy import (
    VacancyCreateDTO,
    VacancyDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    TaskType,
    UserRole,
    VacancyStatus,
)
from competency_system.presentation.api.dependencies import (
    get_assess_candidate_use_case,
    get_authenticate_user_use_case,
    get_current_user,
    get_decide_vacancy_suggestion_use_case,
    get_extract_vacancy_graph_use_case,
    get_finalize_vacancy_graph_use_case,
    get_get_candidate_profile_use_case,
    get_get_task_use_case,
    get_get_vacancy_graph_use_case,
    get_issue_token_pair_use_case,
    get_list_tasks_use_case,
    get_list_vacancy_suggestions_use_case,
    get_rebuild_task_mapping_use_case,
    get_recalculate_ranking_use_case,
    get_refresh_token_data,
    get_refresh_token_from_cookie,
    get_refresh_token_pair_use_case,
    get_sync_tasks_use_case,
    get_validate_task_mapping_use_case,
    get_logout_use_case,
    verify_testing_system_webhook_secret,
)
from competency_system.presentation.api.main import app


@pytest.fixture(autouse=True)
def _clear_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@dataclass
class _StaticUseCase:
    result: object

    async def execute(self, *args: object, **kwargs: object) -> object:
        return self.result


@dataclass
class _LogoutUseCase:
    async def execute(self, *args: object, **kwargs: object) -> None:
        return None


def _sample_vacancy() -> VacancyDTO:
    now = datetime.now(UTC)
    category_id = uuid4()
    competency_id = uuid4()
    sub_id = uuid4()
    sub = SubCompetencyDTO(
        id=sub_id,
        name="REST",
        description="REST APIs",
        target_level=CompetencyLevel.INTERMEDIATE,
        weight=1.0,
    )
    competency = CompetencyDTO(
        id=competency_id,
        category_id=category_id,
        name="Backend",
        description="Core backend",
        is_required=True,
        sub_competencies=[sub],
    )
    category = CategoryDTO(
        id=category_id,
        name="Engineering",
        description="Engineering skills",
        emoji="E",
        competencies=[competency],
    )
    return VacancyDTO(
        id=uuid4(),
        name="Backend Engineer",
        description="Build APIs",
        status=VacancyStatus.READY,
        experience="3+ years",
        key_skills=["python", "sql"],
        categories=[category],
        competencies=[competency],
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def _sample_task() -> TaskDTO:
    now = datetime.now(UTC)
    return TaskDTO(
        id=uuid4(),
        external_id="task-1",
        title="API Task",
        description="Implement API",
        type=TaskType.CODE,
        competency_mappings=[
            TaskCompetencyMappingDTO(sub_competency_id=uuid4(), weight=1.0)
        ],
        mapping_validated=False,
        created_at=now,
        updated_at=now,
    )


def _sample_candidate_profile() -> CandidateProfileDTO:
    return CandidateProfileDTO(
        candidate_id=uuid4(),
        external_id="candidate-1",
        competency_scores=[
            CompetencyScoreDTO(
                competency_id=uuid4(),
                level=CompetencyLevel.ADVANCED,
                confidence=0.8,
            )
        ],
        total_score=80.0,
    )


def _sample_candidate_result() -> CandidateAssessmentResultDTO:
    now = datetime.now(UTC)
    profile = _sample_candidate_profile()
    return CandidateAssessmentResultDTO(
        candidate_profile=profile,
        test_result=TestResultDTO(
            id=uuid4(),
            candidate_id=profile.candidate_id,
            task_id=uuid4(),
            passed=True,
            score=85.0,
            attempts=1,
            code_submitted="print('ok')",
            llm_assessment={"score": 85},
            created_at=now,
        ),
    )


def _sample_ranking(vacancy_id: UUID) -> VacancyRankingDTO:
    return VacancyRankingDTO(
        vacancy_id=vacancy_id,
        rankings=[
            RankingItemDTO(
                candidate_id=uuid4(),
                candidate_external_id="candidate-1",
                total_score=79.0,
                required_match=0.7,
                desired_match=1.0,
                required_score=49.0,
                desired_score=30.0,
                breakdown=[
                    RankingBreakdownItemDTO(
                        competency_id=uuid4(),
                        competency_name="Backend",
                        required=True,
                        matched_weight=0.7,
                        total_weight=1.0,
                        coverage=0.7,
                        score_contribution=49.0,
                        matched_subcompetency_ids=[uuid4()],
                        total_subcompetency_ids=[uuid4()],
                    )
                ],
            )
        ],
    )


def test_auth_routes_contract() -> None:
    user_id = uuid4()
    app.dependency_overrides[get_authenticate_user_use_case] = lambda: _StaticUseCase(
        SimpleNamespace(id=user_id)
    )
    app.dependency_overrides[get_issue_token_pair_use_case] = lambda: _StaticUseCase(
        TokenPairDTO(access_token="access", refresh_token="refresh")
    )
    app.dependency_overrides[get_refresh_token_from_cookie] = lambda: "refresh"
    app.dependency_overrides[get_refresh_token_data] = lambda: RefreshTokenDataDTO(
        user_id=user_id,
        jti=uuid4(),
    )
    app.dependency_overrides[get_refresh_token_pair_use_case] = lambda: _StaticUseCase(
        TokenPairDTO(access_token="access2", refresh_token="refresh2")
    )
    app.dependency_overrides[get_logout_use_case] = lambda: _LogoutUseCase()

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "pass"},
        )
        assert login.status_code == 200
        assert login.json()["access_token"] == "access"

        refresh = client.post("/api/v1/auth/refresh")
        assert refresh.status_code == 200
        assert refresh.json()["access_token"] == "access2"

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204


def test_vacancy_routes_contract() -> None:
    vacancy = _sample_vacancy()
    suggestion = VacancyGraphSuggestionDTO(
        id=uuid4(),
        vacancy_id=vacancy.id,
        stage=SuggestionStage.CATEGORY,
        entity_type=SuggestionEntityType.CATEGORY,
        status=SuggestionStatus.PENDING,
        name="Data",
        description="Data category",
        reason="Useful",
    )

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_extract_vacancy_graph_use_case] = (
        lambda: _StaticUseCase(vacancy)
    )
    app.dependency_overrides[get_get_vacancy_graph_use_case] = (
        lambda: _StaticUseCase(vacancy)
    )
    app.dependency_overrides[get_finalize_vacancy_graph_use_case] = (
        lambda: _StaticUseCase(vacancy)
    )
    app.dependency_overrides[get_list_vacancy_suggestions_use_case] = (
        lambda: _StaticUseCase([suggestion])
    )
    app.dependency_overrides[get_decide_vacancy_suggestion_use_case] = (
        lambda: _StaticUseCase(suggestion)
    )

    with TestClient(app) as client:
        create_payload = VacancyCreateDTO(
            name="Backend Engineer",
            description="Build APIs",
            experience="3+ years",
            key_skills=["python"],
        ).model_dump(mode="json")
        created = client.post("/api/v1/vacancies", json=create_payload)
        assert created.status_code == 201

        fetched = client.get(f"/api/v1/vacancies/{vacancy.id}")
        assert fetched.status_code == 200

        graph = client.get(f"/api/v1/vacancies/{vacancy.id}/graph")
        assert graph.status_code == 200

        patch_payload = VacancyGraphUpdateDTO(
            categories=vacancy.categories,
            suggestion_decisions=[],
            error_message=None,
        ).model_dump(mode="json")
        finalized = client.patch(f"/api/v1/vacancies/{vacancy.id}/graph", json=patch_payload)
        assert finalized.status_code == 200

        suggestions = client.get(f"/api/v1/vacancies/{vacancy.id}/suggestions")
        assert suggestions.status_code == 200
        assert len(suggestions.json()) == 1

        decision = client.post(
            f"/api/v1/vacancies/{vacancy.id}/suggestions/decision",
            json={
                "suggestion_id": str(suggestion.id),
                "status": SuggestionStatus.APPROVED.value,
            },
        )
        assert decision.status_code == 200


def test_tasks_admin_and_webhook_routes_contract() -> None:
    task = _sample_task()
    candidate_result = _sample_candidate_result()

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_sync_tasks_use_case] = lambda: _StaticUseCase(
        SyncTasksResultDTO(synced_tasks=[task])
    )
    app.dependency_overrides[get_get_task_use_case] = lambda: _StaticUseCase(task)
    app.dependency_overrides[get_list_tasks_use_case] = lambda: _StaticUseCase([task])
    app.dependency_overrides[get_rebuild_task_mapping_use_case] = (
        lambda: _StaticUseCase(task)
    )
    app.dependency_overrides[get_validate_task_mapping_use_case] = (
        lambda: _StaticUseCase(task.model_copy(update={"mapping_validated": True}))
    )
    app.dependency_overrides[get_assess_candidate_use_case] = lambda: _StaticUseCase(
        candidate_result
    )
    app.dependency_overrides[verify_testing_system_webhook_secret] = lambda: None

    with TestClient(app) as client:
        sync = client.post("/api/v1/tasks/sync")
        assert sync.status_code == 200

        mapping = client.get(f"/api/v1/tasks/{task.id}/mapping")
        assert mapping.status_code == 200

        list_tasks = client.get("/api/v1/admin/tasks")
        assert list_tasks.status_code == 200
        assert len(list_tasks.json()) == 1

        detail = client.get(f"/api/v1/admin/tasks/{task.id}")
        assert detail.status_code == 200

        rebuild = client.post(f"/api/v1/admin/tasks/{task.id}/mapping/rebuild")
        assert rebuild.status_code == 200

        validate = client.post(f"/api/v1/admin/tasks/{task.id}/mapping/validate")
        assert validate.status_code == 200
        assert validate.json()["mapping_validated"] is True

        webhook = client.post(
            "/api/v1/webhook/task-completed",
            json={
                "candidate_external_id": "candidate-1",
                "task_external_id": "task-1",
                "type": "code",
                "code": "print('ok')",
                "passed": 1,
                "total": 1,
                "attempts": 1,
                "duration_seconds": 10,
            },
        )
        assert webhook.status_code == 200


def test_candidates_and_ranking_routes_contract() -> None:
    vacancy_id = uuid4()
    ranking = _sample_ranking(vacancy_id)
    profile = _sample_candidate_profile()

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_get_candidate_profile_use_case] = (
        lambda: _StaticUseCase(profile)
    )
    app.dependency_overrides[get_recalculate_ranking_use_case] = (
        lambda: _StaticUseCase(ranking)
    )

    with TestClient(app) as client:
        profile_response = client.get(f"/api/v1/candidates/{profile.candidate_id}/profile")
        assert profile_response.status_code == 200

        rankings = client.get(f"/api/v1/vacancies/{vacancy_id}/rankings")
        assert rankings.status_code == 200

        ranking_legacy = client.get(f"/api/v1/vacancies/{vacancy_id}/ranking")
        assert ranking_legacy.status_code == 200

        candidates_legacy = client.get(f"/api/v1/vacancies/{vacancy_id}/candidates")
        assert candidates_legacy.status_code == 200
