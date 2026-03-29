from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from competency_system.application.dtos.auth import (
    UserAdminDTO,
    UserCreateDTO,
    UserRoleUpdateDTO,
    UserStatusUpdateDTO,
)
from competency_system.application.use_cases.auth import (
    CreateUserUseCase,
    ListUsersUseCase,
    UpdateUserRoleUseCase,
    UpdateUserStatusUseCase,
)
from competency_system.presentation.api.dependencies import (
    get_create_user_use_case,
    get_list_users_use_case,
    get_update_user_role_use_case,
    get_update_user_status_use_case,
    require_admin_or_system,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[UserAdminDTO])
async def list_users(
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[ListUsersUseCase, Depends(get_list_users_use_case)],
) -> list[UserAdminDTO]:
    return await use_case.execute()


@router.post("", response_model=UserAdminDTO, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
) -> UserAdminDTO:
    try:
        return await use_case.execute(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{user_id}/role", response_model=UserAdminDTO)
async def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[UpdateUserRoleUseCase, Depends(get_update_user_role_use_case)],
) -> UserAdminDTO:
    try:
        return await use_case.execute(user_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch("/{user_id}/status", response_model=UserAdminDTO)
async def update_user_status(
    user_id: UUID,
    payload: UserStatusUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[
        UpdateUserStatusUseCase, Depends(get_update_user_status_use_case)
    ],
) -> UserAdminDTO:
    try:
        return await use_case.execute(user_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
