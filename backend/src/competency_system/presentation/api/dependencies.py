from __future__ import annotations

from typing import Annotated, cast

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from competency_system.application.dtos.auth import (
    AccessTokenDataDTO,
    CurrentUserDTO,
    LoginDTO,
    RefreshTokenDataDTO,
)
from competency_system.application.ports.external_testing_system import (
    ExternalTestingSystemGateway,
)
from competency_system.application.ports.health import HealthCheckPort
from competency_system.application.ports.llm import LLMGateway
from competency_system.application.ports.llm_jobs import LLMJobQueuePort
from competency_system.application.ports.uow import UnitOfWork
from competency_system.application.use_cases.auth import (
    AuthenticateUserUseCase,
    CreateUserUseCase,
    GetCurrentUserUseCase,
    IssueTokenPairUseCase,
    ListUsersUseCase,
    LogoutUseCase,
    RefreshTokenPairUseCase,
    UpdateUserRoleUseCase,
    UpdateUserStatusUseCase,
)
from competency_system.application.use_cases.candidate import (
    AssessCandidateUseCase,
    DeleteCandidateUseCase,
    GetCandidateProfileUseCase,
    GetCandidateUseCase,
    ListCandidatesUseCase,
    ListVacancyCandidatesUseCase,
)
from competency_system.application.use_cases.health import HealthCheckUseCase
from competency_system.application.use_cases.ontology import (
    CreateCategoryUseCase,
    CreateCompetencyUseCase,
    CreateSubCompetencyUseCase,
    DeleteCategoryUseCase,
    DeleteCompetencyUseCase,
    DeleteSubCompetencyUseCase,
    GetCategoryUseCase,
    GetCompetencyUseCase,
    GetSubCompetencyUseCase,
    ListCategoriesUseCase,
    ListCompetenciesUseCase,
    ListSubCompetenciesUseCase,
    UpdateCategoryUseCase,
    UpdateCompetencyUseCase,
    UpdateSubCompetencyUseCase,
)
from competency_system.application.use_cases.ranking import (
    GetVacancyRankingUseCase,
    RecalculateRankingUseCase,
)
from competency_system.application.use_cases.task import (
    GetTaskUseCase,
    ListTasksUseCase,
    RebuildTaskMappingUseCase,
    ReplaceTaskMappingUseCase,
    SyncTasksUseCase,
    ValidateTaskMappingUseCase,
)
from competency_system.application.use_cases.vacancy import (
    CreateVacancyGraphUseCase,
    DecideVacancySuggestionsUseCase,
    DecideVacancySuggestionUseCase,
    DeleteVacancyUseCase,
    FinalizeVacancyGraphUseCase,
    GetVacancyGraphUseCase,
    HardDeleteVacancyUseCase,
    ListVacanciesForReviewUseCase,
    ListVacanciesUseCase,
    ListVacancySuggestionsUseCase,
    RestoreVacancyUseCase,
    SaveVacancyGraphUseCase,
    UpdateVacancyStatusUseCase,
    UpdateVacancyUseCase,
)
from competency_system.domain.value_objects.enums import UserRole
from competency_system.infrastructure.health.database_health import (
    SQLAlchemyHealthCheckPort,
)
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.infrastructure.security import decode_jwt, oauth2_scheme
from competency_system.presentation.api.runtime_config import (
    AuthCookieConfig,
    RebuildTaskMappingConfig,
)


def get_db_engine(request: Request) -> AsyncEngine:
    return cast(AsyncEngine, request.app.state.db_engine)


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)


def get_uow(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
) -> UnitOfWork:
    return SQLAlchemyUnitOfWork(session_factory)


def get_rebuild_task_mapping_config(request: Request) -> RebuildTaskMappingConfig:
    return cast(RebuildTaskMappingConfig, request.app.state.rebuild_task_mapping_config)


def get_auth_cookie_config(request: Request) -> AuthCookieConfig:
    return cast(AuthCookieConfig, request.app.state.auth_cookie_config)


def get_llm_gateway(request: Request) -> LLMGateway:
    return cast(LLMGateway, request.app.state.llm_gateway)


def get_testing_system_gateway(request: Request) -> ExternalTestingSystemGateway:
    return cast(ExternalTestingSystemGateway, request.app.state.testing_system_gateway)


def get_llm_job_queue(request: Request) -> LLMJobQueuePort:
    return cast(LLMJobQueuePort, request.app.state.llm_job_queue)


# healthcheck


def get_health_check_port(request: Request) -> HealthCheckPort:
    session_factory = cast(
        async_sessionmaker[AsyncSession],
        request.app.state.session_factory,
    )
    return SQLAlchemyHealthCheckPort(session_factory)


def get_health_check_use_case(
    health_check_port: Annotated[HealthCheckPort, Depends(get_health_check_port)],
) -> HealthCheckUseCase:
    return HealthCheckUseCase(health_check_port)


# vacancy use cases


def get_extract_vacancy_graph_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    job_queue: Annotated[LLMJobQueuePort, Depends(get_llm_job_queue)],
) -> CreateVacancyGraphUseCase:
    return CreateVacancyGraphUseCase(uow, job_queue)


def get_get_vacancy_graph_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetVacancyGraphUseCase:
    return GetVacancyGraphUseCase(uow)


def get_save_vacancy_graph_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> SaveVacancyGraphUseCase:
    return SaveVacancyGraphUseCase(uow)


def get_finalize_vacancy_graph_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> FinalizeVacancyGraphUseCase:
    return FinalizeVacancyGraphUseCase(uow)


def get_update_vacancy_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UpdateVacancyUseCase:
    return UpdateVacancyUseCase(uow)


def get_delete_vacancy_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> DeleteVacancyUseCase:
    return DeleteVacancyUseCase(uow)


def get_restore_vacancy_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RestoreVacancyUseCase:
    return RestoreVacancyUseCase(uow)


def get_hard_delete_vacancy_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> HardDeleteVacancyUseCase:
    return HardDeleteVacancyUseCase(uow)


def get_list_vacancy_suggestions_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListVacancySuggestionsUseCase:
    return ListVacancySuggestionsUseCase(uow)


def get_list_vacancies_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListVacanciesUseCase:
    return ListVacanciesUseCase(uow)


def get_update_vacancy_status_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UpdateVacancyStatusUseCase:
    return UpdateVacancyStatusUseCase(uow)


def get_list_vacancies_for_review_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListVacanciesForReviewUseCase:
    return ListVacanciesForReviewUseCase(uow)


def get_decide_vacancy_suggestion_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> DecideVacancySuggestionUseCase:
    return DecideVacancySuggestionUseCase(uow)


def get_decide_vacancy_suggestions_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> DecideVacancySuggestionsUseCase:
    return DecideVacancySuggestionsUseCase(uow)


# ontology use cases


def get_list_categories_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListCategoriesUseCase:
    return ListCategoriesUseCase(uow=uow)


def get_get_category_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetCategoryUseCase:
    return GetCategoryUseCase(uow=uow)


def get_create_category_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> CreateCategoryUseCase:
    return CreateCategoryUseCase(uow=uow)


def get_update_category_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UpdateCategoryUseCase:
    return UpdateCategoryUseCase(uow=uow)


def get_delete_category_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> DeleteCategoryUseCase:
    return DeleteCategoryUseCase(uow=uow)


def get_list_competencies_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListCompetenciesUseCase:
    return ListCompetenciesUseCase(uow=uow)


def get_get_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetCompetencyUseCase:
    return GetCompetencyUseCase(uow=uow)


def get_create_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> CreateCompetencyUseCase:
    return CreateCompetencyUseCase(uow=uow)


def get_update_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UpdateCompetencyUseCase:
    return UpdateCompetencyUseCase(uow=uow)


def get_delete_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> DeleteCompetencyUseCase:
    return DeleteCompetencyUseCase(uow=uow)


def get_list_sub_competencies_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListSubCompetenciesUseCase:
    return ListSubCompetenciesUseCase(uow=uow)


def get_get_sub_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetSubCompetencyUseCase:
    return GetSubCompetencyUseCase(uow=uow)


def get_create_sub_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> CreateSubCompetencyUseCase:
    return CreateSubCompetencyUseCase(uow=uow)


def get_update_sub_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UpdateSubCompetencyUseCase:
    return UpdateSubCompetencyUseCase(uow=uow)


def get_delete_sub_competency_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> DeleteSubCompetencyUseCase:
    return DeleteSubCompetencyUseCase(uow=uow)


# tasks use cases


def get_sync_tasks_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    gateway: Annotated[
        ExternalTestingSystemGateway, Depends(get_testing_system_gateway)
    ],
    job_queue: Annotated[LLMJobQueuePort, Depends(get_llm_job_queue)],
) -> SyncTasksUseCase:
    return SyncTasksUseCase(uow, gateway, job_queue)


def get_get_task_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetTaskUseCase:
    return GetTaskUseCase(uow)


def get_assess_candidate_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    llm_gateway: Annotated[LLMGateway, Depends(get_llm_gateway)],
    job_queue: Annotated[LLMJobQueuePort, Depends(get_llm_job_queue)],
) -> AssessCandidateUseCase:
    return AssessCandidateUseCase(uow, job_queue, llm_gateway)


def get_list_tasks_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListTasksUseCase:
    return ListTasksUseCase(uow)


def get_rebuild_task_mapping_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    llm_gateway: Annotated[LLMGateway, Depends(get_llm_gateway)],
    job_queue: Annotated[LLMJobQueuePort, Depends(get_llm_job_queue)],
    config: Annotated[
        RebuildTaskMappingConfig, Depends(get_rebuild_task_mapping_config)
    ],
) -> RebuildTaskMappingUseCase:
    return RebuildTaskMappingUseCase(
        uow,
        llm_gateway,
        job_queue,
        max_parallel_requests=config.max_parallel_requests,
        stage_timeout_seconds=config.stage_timeout_seconds,
        prompt_version=config.task_prompt_version,
    )


def get_validate_task_mapping_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ValidateTaskMappingUseCase:
    return ValidateTaskMappingUseCase(uow)


def get_replace_task_mapping_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ReplaceTaskMappingUseCase:
    return ReplaceTaskMappingUseCase(uow)


# candidates use cases


def get_get_candidate_profile_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetCandidateProfileUseCase:
    return GetCandidateProfileUseCase(uow)


def get_list_candidates_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListCandidatesUseCase:
    return ListCandidatesUseCase(uow)


def get_get_candidate_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetCandidateUseCase:
    return GetCandidateUseCase(uow)


def get_delete_candidate_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> DeleteCandidateUseCase:
    return DeleteCandidateUseCase(uow)


def get_list_vacancy_candidates_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListVacancyCandidatesUseCase:
    return ListVacancyCandidatesUseCase(uow)


def get_recalculate_ranking_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RecalculateRankingUseCase:
    return RecalculateRankingUseCase(uow)


def get_get_vacancy_ranking_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetVacancyRankingUseCase:
    return GetVacancyRankingUseCase(uow)


# auth  cases


def get_authenticate_user_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(uow=uow)


def get_issue_token_pair_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> IssueTokenPairUseCase:
    return IssueTokenPairUseCase(uow=uow)


def get_refresh_token_pair_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RefreshTokenPairUseCase:
    return RefreshTokenPairUseCase(uow=uow)


def get_logout_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> LogoutUseCase:
    return LogoutUseCase(uow=uow)


def get_get_current_user_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> GetCurrentUserUseCase:
    return GetCurrentUserUseCase(uow=uow)


def get_list_users_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ListUsersUseCase:
    return ListUsersUseCase(uow=uow)


def get_create_user_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> CreateUserUseCase:
    return CreateUserUseCase(uow=uow)


def get_update_user_role_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UpdateUserRoleUseCase:
    return UpdateUserRoleUseCase(uow=uow)


def get_update_user_status_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UpdateUserStatusUseCase:
    return UpdateUserStatusUseCase(uow=uow)


def get_login_data(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> LoginDTO:
    try:
        return LoginDTO(email=form_data.username, password=form_data.password)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from None


# tokens


def get_refresh_token_from_cookie(request: Request) -> str:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    return refresh_token


def get_access_token_data(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> AccessTokenDataDTO:
    try:
        payload = decode_jwt(token)
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return AccessTokenDataDTO(user_id=user_id, role=role)
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_refresh_token_data(
    refresh_token: Annotated[str, Depends(get_refresh_token_from_cookie)],
) -> RefreshTokenDataDTO:
    try:
        payload = decode_jwt(refresh_token)
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if user_id is None or jti is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return RefreshTokenDataDTO(user_id=user_id, jti=jti)
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_current_user(
    access_token_data: Annotated[AccessTokenDataDTO, Depends(get_access_token_data)],
) -> CurrentUserDTO:
    return CurrentUserDTO(
        user_id=access_token_data.user_id, role=access_token_data.role
    )


def _verify_roles(current_user: CurrentUserDTO, allowed_roles: set[UserRole]) -> None:
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def require_admin_or_expert(
    current_user: Annotated[CurrentUserDTO, Depends(get_current_user)],
) -> None:
    _verify_roles(current_user, {UserRole.ADMIN, UserRole.EXPERT})


def require_hr_expert_admin(
    current_user: Annotated[CurrentUserDTO, Depends(get_current_user)],
) -> None:
    _verify_roles(current_user, {UserRole.ADMIN, UserRole.EXPERT, UserRole.HR})


def require_admin_or_system(
    current_user: Annotated[CurrentUserDTO, Depends(get_current_user)],
) -> None:
    _verify_roles(current_user, {UserRole.ADMIN, UserRole.SYSTEM})


def verify_testing_system_webhook_secret(
    request: Request,
    webhook_secret: Annotated[str | None, Header(alias="X-Webhook-Secret")] = None,
) -> None:
    expected_secret = cast(
        str,
        getattr(request.app.state, "testing_system_webhook_secret", ""),
    )
    if not expected_secret:
        return
    if webhook_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret",
        )
