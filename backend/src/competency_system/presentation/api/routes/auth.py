from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from competency_system.application.dtos.auth import (
    LoginDTO,
    RefreshTokenDataDTO,
    TokenResponseDTO,
)
from competency_system.application.use_cases.auth import (
    AuthenticateUserUseCase,
    IssueTokenPairUseCase,
    LogoutUseCase,
    RefreshTokenPairUseCase,
)
from competency_system.infrastructure.settings import Settings
from competency_system.presentation.api.dependencies import (
    get_app_settings,
    get_authenticate_user_use_case,
    get_issue_token_pair_use_case,
    get_login_data,
    get_logout_use_case,
    get_refresh_token_data,
    get_refresh_token_from_cookie,
    get_refresh_token_pair_use_case,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponseDTO)
async def login(
    response: Response,
    credentials: Annotated[LoginDTO, Depends(get_login_data)],
    auth_use_case: Annotated[AuthenticateUserUseCase, Depends(get_authenticate_user_use_case)],
    issue_token_pair_use_case: Annotated[
        IssueTokenPairUseCase,
        Depends(get_issue_token_pair_use_case),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> TokenResponseDTO:
    user = await auth_use_case.execute(credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_pair = await issue_token_pair_use_case.execute(user_id=user.id)
    if token_pair is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _set_refresh_cookie(response, token_pair.refresh_token, settings)
    return TokenResponseDTO(access_token=token_pair.access_token)


@router.post("/refresh", response_model=TokenResponseDTO)
async def refresh_token(
    response: Response,
    refresh_token_raw: Annotated[str, Depends(get_refresh_token_from_cookie)],
    refresh_token_data: Annotated[RefreshTokenDataDTO, Depends(get_refresh_token_data)],
    refresh_use_case: Annotated[RefreshTokenPairUseCase, Depends(get_refresh_token_pair_use_case)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> TokenResponseDTO:
    token_pair = await refresh_use_case.execute(
        refresh_token_raw=refresh_token_raw,
        token_data=refresh_token_data,
    )
    if token_pair is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _set_refresh_cookie(response, token_pair.refresh_token, settings)
    return TokenResponseDTO(access_token=token_pair.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token_data: Annotated[RefreshTokenDataDTO, Depends(get_refresh_token_data)],
    logout_use_case: Annotated[LogoutUseCase, Depends(get_logout_use_case)],
) -> None:
    await logout_use_case.execute(refresh_token_data)
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
