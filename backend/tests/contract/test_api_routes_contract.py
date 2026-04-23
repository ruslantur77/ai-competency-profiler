from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from competency_system.application.dtos.auth import (
    CurrentUserDetailsDTO,
    CurrentUserDTO,
    RefreshTokenDataDTO,
    TokenPairDTO,
)
from competency_system.application.dtos.candidate import CandidateListItemDto
from competency_system.application.dtos.competency import (
    CategoryDTO,
    CompetencyDTO,
    SubCompetencyDTO,
)
from competency_system.application.dtos.task import SyncTasksResultDTO
from competency_system.application.dtos.vacancy import (
    VacancyCreateDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
    VacancyUpdateDTO,
)
from competency_system.application.errors import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    AssessmentStatus,
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    UserRole,
    VacancyStatus,
)
from competency_system.presentation.api.dependencies import (
    get_assess_candidate_use_case,
    get_authenticate_user_use_case,
    get_create_category_use_case,
    get_create_competency_use_case,
    get_create_sub_competency_use_case,
    get_current_user,
    get_decide_vacancy_suggestion_use_case,
    get_decide_vacancy_suggestions_use_case,
    get_delete_candidate_use_case,
    get_delete_category_use_case,
    get_delete_competency_use_case,
    get_delete_sub_competency_use_case,
    get_delete_vacancy_use_case,
    get_extract_vacancy_graph_use_case,
    get_finalize_task_graph_use_case,
    get_finalize_vacancy_graph_use_case,
    get_get_candidate_profile_use_case,
    get_get_candidate_use_case,
    get_get_category_use_case,
    get_get_competency_use_case,
    get_get_current_user_use_case,
    get_get_sub_competency_use_case,
    get_get_task_graph_use_case,
    get_get_vacancy_graph_use_case,
    get_get_vacancy_ranking_use_case,
    get_hard_delete_vacancy_use_case,
    get_issue_token_pair_use_case,
    get_list_candidates_use_case,
    get_list_categories_use_case,
    get_list_competencies_use_case,
    get_list_sub_competencies_use_case,
    get_list_tasks_use_case,
    get_list_vacancies_use_case,
    get_list_vacancy_candidates_use_case,
    get_list_vacancy_suggestions_use_case,
    get_logout_use_case,
    get_recalculate_ranking_use_case,
    get_refresh_token_data,
    get_refresh_token_from_cookie,
    get_refresh_token_pair_use_case,
    get_restore_vacancy_use_case,
    get_save_task_graph_use_case,
    get_save_vacancy_graph_use_case,
    get_sync_tasks_use_case,
    get_update_category_use_case,
    get_update_competency_use_case,
    get_update_sub_competency_use_case,
    get_update_task_status_use_case,
    get_update_vacancy_use_case,
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


@dataclass
class _RaisingUseCase:
    error: Exception

    async def execute(self, *args: object, **kwargs: object) -> object:
        raise self.error


def test_auth_routes_contract() -> None:
    user_id = uuid4()
    current_user = CurrentUserDTO(user_id=user_id, role=UserRole.ADMIN)
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
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_get_current_user_use_case] = lambda: _StaticUseCase(
        CurrentUserDetailsDTO(
            id=user_id,
            email="admin@example.com",
            role=UserRole.ADMIN,
            is_active=True,
        )
    )

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

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["id"] == str(user_id)
        assert me.json()["email"] == "admin@example.com"

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204


def test_vacancy_routes_contract(api_dto_factory: ApiDTOFactory) -> None:
    vacancy = api_dto_factory.make_vacancy()
    vacancy_candidates = [
        CandidateListItemDto(
            id=uuid4(),
            external_id="candidate-1",
            vacancy_id=vacancy.id,
            status=AssessmentStatus.PENDING,
            last_assessment_at=None,
        )
    ]
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
    app.dependency_overrides[get_list_vacancies_use_case] = lambda: _StaticUseCase(
        SimpleNamespace(items=[vacancy], total=1, limit=50, offset=0)
    )
    app.dependency_overrides[get_save_vacancy_graph_use_case] = lambda: _StaticUseCase(
        vacancy
    )
    app.dependency_overrides[get_update_vacancy_use_case] = lambda: _StaticUseCase(
        vacancy.model_copy(update={"name": "Senior Backend Engineer"})
    )
    app.dependency_overrides[get_finalize_vacancy_graph_use_case] = lambda: (
        _StaticUseCase(vacancy.model_copy(update={"status": VacancyStatus.READY}))
    )
    app.dependency_overrides[get_delete_vacancy_use_case] = lambda: _StaticUseCase(None)
    app.dependency_overrides[get_restore_vacancy_use_case] = lambda: _StaticUseCase(
        vacancy
    )
    app.dependency_overrides[get_hard_delete_vacancy_use_case] = lambda: _StaticUseCase(
        None
    )
    app.dependency_overrides[get_list_vacancy_suggestions_use_case] = lambda: (
        _StaticUseCase([suggestion])
    )
    app.dependency_overrides[get_decide_vacancy_suggestion_use_case] = lambda: (
        _StaticUseCase(suggestion)
    )
    app.dependency_overrides[get_decide_vacancy_suggestions_use_case] = lambda: (
        _StaticUseCase([suggestion])
    )
    app.dependency_overrides[get_list_vacancy_candidates_use_case] = lambda: (
        _StaticUseCase(vacancy_candidates)
    )

    with TestClient(app) as client:
        create_payload = VacancyCreateDTO(
            name="Backend Engineer",
            description="Build APIs",
        ).model_dump(mode="json")
        created = client.post("/api/v1/vacancies", json=create_payload)
        assert created.status_code == 201

        listed = client.get("/api/v1/vacancies")
        assert listed.status_code == 200
        listed_payload = listed.json()
        assert listed_payload["total"] == 1
        assert len(listed_payload["items"]) == 1

        listed_filtered = client.get(
            "/api/v1/vacancies",
            params=[("status_filter", "draft"), ("status_filter", "ready")],
        )
        assert listed_filtered.status_code == 200

        fetched = client.get(f"/api/v1/vacancies/{vacancy.id}")
        assert fetched.status_code == 200

        graph = client.get(f"/api/v1/vacancies/{vacancy.id}/graph")
        assert graph.status_code == 200

        update_payload = VacancyUpdateDTO(
            name="Senior Backend Engineer",
        ).model_dump(mode="json")
        updated = client.patch(f"/api/v1/vacancies/{vacancy.id}", json=update_payload)
        assert updated.status_code == 200
        assert updated.json()["name"] == "Senior Backend Engineer"

        patch_payload = VacancyGraphUpdateDTO(
            categories=[],
            error_message=None,
        ).model_dump(mode="json")
        finalized = client.patch(
            f"/api/v1/vacancies/{vacancy.id}/graph", json=patch_payload
        )
        assert finalized.status_code == 200

        legacy_payload = {
            "categories": [],
            "error_message": None,
            "suggestion_decisions": [],
        }
        finalized_legacy = client.patch(
            f"/api/v1/vacancies/{vacancy.id}/graph", json=legacy_payload
        )
        assert finalized_legacy.status_code == 422

        finalized_status = client.post(f"/api/v1/vacancies/{vacancy.id}/graph/finalize")
        assert finalized_status.status_code == 200

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

        bulk_decision = client.post(
            f"/api/v1/vacancies/{vacancy.id}/suggestions/decisions",
            json={
                "decisions": [
                    {
                        "suggestion_id": str(suggestion.id),
                        "status": SuggestionStatus.REJECTED.value,
                    }
                ]
            },
        )
        assert bulk_decision.status_code == 200
        assert len(bulk_decision.json()) == 1

        candidates = client.get(f"/api/v1/vacancies/{vacancy.id}/candidates")
        assert candidates.status_code == 200
        assert len(candidates.json()) == 1
        assert candidates.json()[0]["external_id"] == "candidate-1"

        deleted = client.delete(f"/api/v1/vacancies/{vacancy.id}")
        assert deleted.status_code == 204

        restored = client.post(f"/api/v1/vacancies/{vacancy.id}/restore")
        assert restored.status_code == 200

        hard_deleted = client.delete(f"/api/v1/vacancies/{vacancy.id}/hard")
        assert hard_deleted.status_code == 204


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
    app.dependency_overrides[get_get_task_graph_use_case] = lambda: _StaticUseCase(task)
    app.dependency_overrides[get_save_task_graph_use_case] = lambda: _StaticUseCase(
        task
    )
    app.dependency_overrides[get_list_tasks_use_case] = lambda: _StaticUseCase(
        SimpleNamespace(items=[task], total=1, limit=50, offset=0)
    )
    app.dependency_overrides[get_finalize_task_graph_use_case] = lambda: _StaticUseCase(
        task
    )
    app.dependency_overrides[get_update_task_status_use_case] = lambda: _StaticUseCase(
        task
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

        app.dependency_overrides[get_sync_tasks_use_case] = lambda: _RaisingUseCase(
            ServiceUnavailableError("Testing system is unavailable")
        )
        sync_unavailable = client.post(
            "/api/v1/tasks/sync",
            json={
                "start": "2026-04-01T00:00:00Z",
                "end": "2026-04-02T00:00:00Z",
                "force": False,
            },
        )
        assert sync_unavailable.status_code == 503
        unavailable_payload = sync_unavailable.json()
        assert unavailable_payload["code"] == "service_unavailable"
        assert unavailable_payload["request_id"]

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

        graph = client.get(f"/api/v1/tasks/{task.id}")
        assert graph.status_code == 200

        save_graph = client.patch(
            f"/api/v1/tasks/{task.id}/graph",
            json={
                "categories": [
                    {
                        "mode": "new",
                        "temp_id": str(uuid4()),
                        "name": "Engineering",
                        "description": "Core",
                        "emoji": "E",
                        "competencies": [],
                    }
                ],
                "error_message": None,
            },
        )
        assert save_graph.status_code == 200

        list_tasks = client.get("/api/v1/tasks")
        assert list_tasks.status_code == 200
        list_tasks_payload = list_tasks.json()
        assert list_tasks_payload["total"] == 1
        assert len(list_tasks_payload["items"]) == 1

        detail = client.get(f"/api/v1/tasks/{task.id}")
        assert detail.status_code == 200

        finalize = client.post(f"/api/v1/tasks/{task.id}/graph/finalize")
        assert finalize.status_code == 200

        update_status = client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "draft"},
        )
        assert update_status.status_code == 200

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


def test_ontology_routes_contract() -> None:
    category_id = uuid4()
    competency_id = uuid4()
    sub_competency_id = uuid4()

    sub = SubCompetencyDTO(
        id=sub_competency_id,
        competency_id=competency_id,
        name="REST",
        description="HTTP APIs",
        weight=1.0,
        target_level=CompetencyLevel.BEGINNER,
    )
    competency = CompetencyDTO(
        id=competency_id,
        category_id=category_id,
        name="Backend",
        description="Backend systems",
        sub_competencies=[sub],
    )
    category = CategoryDTO(
        id=category_id,
        name="Engineering",
        description="Engineering skills",
        emoji="🛠",
        competencies=[competency],
    )

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_list_categories_use_case] = lambda: _StaticUseCase(
        [category]
    )
    app.dependency_overrides[get_get_category_use_case] = lambda: _StaticUseCase(
        category
    )
    app.dependency_overrides[get_create_category_use_case] = lambda: _StaticUseCase(
        category
    )
    app.dependency_overrides[get_update_category_use_case] = lambda: _StaticUseCase(
        category
    )
    app.dependency_overrides[get_delete_category_use_case] = lambda: _StaticUseCase(
        None
    )

    app.dependency_overrides[get_list_competencies_use_case] = lambda: _StaticUseCase(
        [competency]
    )
    app.dependency_overrides[get_get_competency_use_case] = lambda: _StaticUseCase(
        competency
    )
    app.dependency_overrides[get_create_competency_use_case] = lambda: _StaticUseCase(
        competency
    )
    app.dependency_overrides[get_update_competency_use_case] = lambda: _StaticUseCase(
        competency
    )
    app.dependency_overrides[get_delete_competency_use_case] = lambda: _StaticUseCase(
        None
    )

    app.dependency_overrides[get_list_sub_competencies_use_case] = lambda: (
        _StaticUseCase([sub])
    )
    app.dependency_overrides[get_get_sub_competency_use_case] = lambda: _StaticUseCase(
        sub
    )
    app.dependency_overrides[get_create_sub_competency_use_case] = lambda: (
        _StaticUseCase(sub)
    )
    app.dependency_overrides[get_update_sub_competency_use_case] = lambda: (
        _StaticUseCase(sub)
    )
    app.dependency_overrides[get_delete_sub_competency_use_case] = lambda: (
        _StaticUseCase(None)
    )

    with TestClient(app) as client:
        categories = client.get("/api/v1/ontology/categories")
        assert categories.status_code == 200
        assert len(categories.json()) == 1

        category_detail = client.get(f"/api/v1/ontology/categories/{category_id}")
        assert category_detail.status_code == 200

        category_create = client.post(
            "/api/v1/ontology/categories",
            json={
                "name": "Engineering",
                "description": "Engineering skills",
                "emoji": "🛠",
            },
        )
        assert category_create.status_code == 201

        category_patch = client.patch(
            f"/api/v1/ontology/categories/{category_id}",
            json={"description": "Updated"},
        )
        assert category_patch.status_code == 200

        competencies = client.get("/api/v1/ontology/competencies")
        assert competencies.status_code == 200
        assert len(competencies.json()) == 1

        competency_detail = client.get(f"/api/v1/ontology/competencies/{competency_id}")
        assert competency_detail.status_code == 200

        competency_create = client.post(
            "/api/v1/ontology/competencies",
            json={
                "category_id": str(category_id),
                "name": "Backend",
                "description": "Backend systems",
            },
        )
        assert competency_create.status_code == 201

        competency_patch = client.patch(
            f"/api/v1/ontology/competencies/{competency_id}",
            json={"name": "Backend Core"},
        )
        assert competency_patch.status_code == 200

        sub_competencies = client.get("/api/v1/ontology/sub-competencies")
        assert sub_competencies.status_code == 200
        assert len(sub_competencies.json()) == 1

        sub_detail = client.get(
            f"/api/v1/ontology/sub-competencies/{sub_competency_id}"
        )
        assert sub_detail.status_code == 200

        sub_create = client.post(
            "/api/v1/ontology/sub-competencies",
            json={
                "competency_id": str(competency_id),
                "name": "REST",
                "description": "HTTP APIs",
                "weight": 1.0,
                "target_level": 2,
            },
        )
        assert sub_create.status_code == 201

        sub_patch = client.patch(
            f"/api/v1/ontology/sub-competencies/{sub_competency_id}",
            json={"weight": 0.8},
        )
        assert sub_patch.status_code == 200

        category_delete = client.delete(f"/api/v1/ontology/categories/{category_id}")
        assert category_delete.status_code == 204

        competency_delete = client.delete(
            f"/api/v1/ontology/competencies/{competency_id}"
        )
        assert competency_delete.status_code == 204

        sub_delete = client.delete(
            f"/api/v1/ontology/sub-competencies/{sub_competency_id}"
        )
        assert sub_delete.status_code == 204


def test_ontology_delete_routes_error_mapping_contract() -> None:
    category_id = uuid4()
    competency_id = uuid4()
    sub_competency_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_delete_category_use_case] = lambda: _RaisingUseCase(
        NotFoundError("Category not found")
    )
    app.dependency_overrides[get_delete_competency_use_case] = lambda: _RaisingUseCase(
        ConflictError("Used in vacancy graph")
    )
    app.dependency_overrides[get_delete_sub_competency_use_case] = lambda: (
        _RaisingUseCase(ConflictError("Used in task mappings"))
    )

    with TestClient(app) as client:
        category_delete = client.delete(f"/api/v1/ontology/categories/{category_id}")
        assert category_delete.status_code == 404
        payload_404 = category_delete.json()
        assert payload_404["code"] == "not_found"
        assert payload_404["message"] == "Category not found"
        assert "request_id" in payload_404

        competency_delete = client.delete(
            f"/api/v1/ontology/competencies/{competency_id}"
        )
        assert competency_delete.status_code == 409
        payload_409 = competency_delete.json()
        assert payload_409["code"] == "conflict"
        assert payload_409["message"] == "Used in vacancy graph"
        assert "request_id" in payload_409

        sub_delete = client.delete(
            f"/api/v1/ontology/sub-competencies/{sub_competency_id}"
        )
        assert sub_delete.status_code == 409


def test_candidates_and_ranking_routes_contract(
    api_dto_factory: ApiDTOFactory,
) -> None:
    vacancy_id = uuid4()
    ranking = api_dto_factory.make_ranking(vacancy_id)
    profile = api_dto_factory.make_candidate_profile()
    candidate = CandidateListItemDto(
        id=profile.candidate_id,
        external_id=profile.external_id,
        vacancy_id=vacancy_id,
        status=AssessmentStatus.COMPLETED,
        last_assessment_at=None,
        deleted_at=None,
    )

    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=uuid4(), role=UserRole.ADMIN
    )
    app.dependency_overrides[get_get_candidate_profile_use_case] = lambda: (
        _StaticUseCase(profile)
    )
    app.dependency_overrides[get_list_candidates_use_case] = lambda: _StaticUseCase(
        SimpleNamespace(items=[candidate], total=1, limit=50, offset=0)
    )
    app.dependency_overrides[get_get_candidate_use_case] = lambda: _StaticUseCase(
        candidate
    )
    app.dependency_overrides[get_delete_candidate_use_case] = lambda: _StaticUseCase(
        None
    )
    app.dependency_overrides[get_recalculate_ranking_use_case] = lambda: _StaticUseCase(
        ranking
    )
    app.dependency_overrides[get_get_vacancy_ranking_use_case] = lambda: _StaticUseCase(
        ranking
    )

    with TestClient(app) as client:
        candidates = client.get("/api/v1/candidates")
        assert candidates.status_code == 200
        payload = candidates.json()
        assert payload["total"] == 1
        assert len(payload["items"]) == 1

        candidate_detail = client.get(f"/api/v1/candidates/{profile.candidate_id}")
        assert candidate_detail.status_code == 200

        profile_response = client.get(
            f"/api/v1/candidates/{profile.candidate_id}/profile"
        )
        assert profile_response.status_code == 200

        deleted = client.delete(f"/api/v1/candidates/{profile.candidate_id}")
        assert deleted.status_code == 204

        rankings = client.get(f"/api/v1/vacancies/{vacancy_id}/rankings")
        assert rankings.status_code == 200

        ranking_legacy = client.get(f"/api/v1/vacancies/{vacancy_id}/ranking")
        assert ranking_legacy.status_code == 200
