from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from competency_system.application.dtos.auth import (
    CurrentUserDTO,
    RefreshTokenDataDTO,
    TokenPairDTO,
)
from competency_system.application.dtos.task import SyncTasksResultDTO
from competency_system.application.dtos.vacancy import (
    VacancyCreateDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
)
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    UserRole,
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
    get_get_vacancy_ranking_use_case,
    get_issue_token_pair_use_case,
    get_list_tasks_use_case,
    get_list_vacancy_suggestions_use_case,
    get_logout_use_case,
    get_rebuild_task_mapping_use_case,
    get_recalculate_ranking_use_case,
    get_refresh_token_data,
    get_refresh_token_from_cookie,
    get_refresh_token_pair_use_case,
    get_sync_tasks_use_case,
    get_validate_task_mapping_use_case,
    verify_testing_system_webhook_secret,
)
from competency_system.presentation.api.main import app
from tests.factories.dto import ApiDTOFactory

pytestmark = pytest.mark.contract


@dataclass
class _StaticUseCase:
    result: object

    async def execute(self, *args: object, **kwargs: object) -> object:
        return self.result


@dataclass
class _LogoutUseCase:
    async def execute(self, *args: object, **kwargs: object) -> None:
        return None


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


def test_vacancy_routes_contract(api_dto_factory: ApiDTOFactory) -> None:
    vacancy = api_dto_factory.make_vacancy()
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
    app.dependency_overrides[get_extract_vacancy_graph_use_case] = lambda: (
        _StaticUseCase(vacancy)
    )
    app.dependency_overrides[get_get_vacancy_graph_use_case] = lambda: _StaticUseCase(
        vacancy
    )
    app.dependency_overrides[get_finalize_vacancy_graph_use_case] = lambda: (
        _StaticUseCase(vacancy)
    )
    app.dependency_overrides[get_list_vacancy_suggestions_use_case] = lambda: (
        _StaticUseCase([suggestion])
    )
    app.dependency_overrides[get_decide_vacancy_suggestion_use_case] = lambda: (
        _StaticUseCase(suggestion)
    )

    with TestClient(app) as client:
        create_payload = VacancyCreateDTO(
            name="Backend Engineer",
            description="Build APIs",
        ).model_dump(mode="json")
        created = client.post("/api/v1/vacancies", json=create_payload)
        assert created.status_code == 201

        fetched = client.get(f"/api/v1/vacancies/{vacancy.id}")
        assert fetched.status_code == 200

        graph = client.get(f"/api/v1/vacancies/{vacancy.id}/graph")
        assert graph.status_code == 200

        patch_payload = VacancyGraphUpdateDTO(
            categories=[],
            suggestion_decisions=[],
            error_message=None,
        ).model_dump(mode="json")
        finalized = client.patch(
            f"/api/v1/vacancies/{vacancy.id}/graph", json=patch_payload
        )
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


def test_tasks_admin_and_webhook_routes_contract(
    api_dto_factory: ApiDTOFactory,
) -> None:
    task = api_dto_factory.make_task()
    candidate_result = api_dto_factory.make_candidate_result()

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_sync_tasks_use_case] = lambda: _StaticUseCase(
        SyncTasksResultDTO(synced_tasks=[task])
    )
    app.dependency_overrides[get_get_task_use_case] = lambda: _StaticUseCase(task)
    app.dependency_overrides[get_list_tasks_use_case] = lambda: _StaticUseCase([task])
    app.dependency_overrides[get_rebuild_task_mapping_use_case] = lambda: (
        _StaticUseCase(task)
    )
    app.dependency_overrides[get_validate_task_mapping_use_case] = lambda: (
        _StaticUseCase(task.model_copy(update={"mapping_validated": True}))
    )
    app.dependency_overrides[get_assess_candidate_use_case] = lambda: _StaticUseCase(
        candidate_result
    )
    app.dependency_overrides[verify_testing_system_webhook_secret] = lambda: None

    with TestClient(app) as client:
        sync = client.post(
            "/api/v1/tasks/sync",
            json={
                "start": "2026-04-01T00:00:00Z",
                "end": "2026-04-02T00:00:00Z",
                "force": True,
            },
        )
        assert sync.status_code == 200

        sync_missing_body = client.post("/api/v1/tasks/sync")
        assert sync_missing_body.status_code == 422
        sync_non_utc = client.post(
            "/api/v1/tasks/sync",
            json={
                "start": "2026-04-01T00:00:00+03:00",
                "end": "2026-04-02T00:00:00Z",
            },
        )
        assert sync_non_utc.status_code == 422

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
                "event_id": str(uuid4()),
                "vacancy_id": str(uuid4()),
                "candidate_external_id": "candidate-1",
                "task_external_id": "task-1",
                "type": "code",
                "code": "print('ok')",
                "question_answers": [],
                "passed": 1,
                "total": 1,
                "attempts": 1,
                "duration_seconds": 10,
            },
        )
        assert webhook.status_code == 200


def test_candidates_and_ranking_routes_contract(
    api_dto_factory: ApiDTOFactory,
) -> None:
    vacancy_id = uuid4()
    ranking = api_dto_factory.make_ranking(vacancy_id)
    profile = api_dto_factory.make_candidate_profile()

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_get_candidate_profile_use_case] = lambda: (
        _StaticUseCase(profile)
    )
    app.dependency_overrides[get_recalculate_ranking_use_case] = lambda: _StaticUseCase(
        ranking
    )
    app.dependency_overrides[get_get_vacancy_ranking_use_case] = lambda: _StaticUseCase(
        ranking
    )

    with TestClient(app) as client:
        profile_response = client.get(
            f"/api/v1/candidates/{profile.candidate_id}/profile"
        )
        assert profile_response.status_code == 200

        rankings = client.get(f"/api/v1/vacancies/{vacancy_id}/rankings")
        assert rankings.status_code == 200

        ranking_legacy = client.get(f"/api/v1/vacancies/{vacancy_id}/ranking")
        assert ranking_legacy.status_code == 200

        candidates_legacy = client.get(f"/api/v1/vacancies/{vacancy_id}/candidates")
        assert candidates_legacy.status_code == 200
