from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams

from competency_system.application.dtos.auth import (
    CurrentUserDTO,
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
    get_current_user,
    get_update_user_role_use_case,
    get_update_user_status_use_case,
    require_admin_or_system,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=LimitOffsetPage[UserAdminDTO])
async def list_users(
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[ListUsersUseCase, Depends(get_list_users_use_case)],
    params: Annotated[LimitOffsetParams, Depends()],
) -> LimitOffsetPage[UserAdminDTO]:
    result = await use_case.execute(limit=params.limit, offset=params.offset)
    return LimitOffsetPage.create(
        items=result.items,
        total=result.total,
        params=params,
    )


@router.post("", response_model=UserAdminDTO, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
) -> UserAdminDTO:
    return await use_case.execute(payload)


@router.patch("/{user_id}/role", response_model=UserAdminDTO)
async def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    current_user: Annotated[CurrentUserDTO, Depends(get_current_user)],
    use_case: Annotated[UpdateUserRoleUseCase, Depends(get_update_user_role_use_case)],
) -> UserAdminDTO:
    return await use_case.execute(
        user_id,
        payload,
        actor_user_id=current_user.user_id,
    )


@router.patch("/{user_id}/status", response_model=UserAdminDTO)
async def update_user_status(
    user_id: UUID,
    payload: UserStatusUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    current_user: Annotated[CurrentUserDTO, Depends(get_current_user)],
    use_case: Annotated[
        UpdateUserStatusUseCase, Depends(get_update_user_status_use_case)
    ],
) -> UserAdminDTO:
    return await use_case.execute(
        user_id,
        payload,
        actor_user_id=current_user.user_id,
    )
