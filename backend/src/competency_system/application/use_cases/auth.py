from __future__ import annotations

from uuid import UUID, uuid4

from competency_system.application.dtos.auth import (
    AccessTokenDataDTO,
    CurrentUserDetailsDTO,
    CurrentUserDTO,
    LoginDTO,
    RefreshTokenDataDTO,
    TokenPairDTO,
    UserAdminDTO,
    UserCreateDTO,
    UserRoleUpdateDTO,
    UserStatusUpdateDTO,
)
from competency_system.application.dtos.pagination import PaginatedItemsDTO
from competency_system.application.errors import ConflictError, NotFoundError
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.entities import User
from competency_system.infrastructure.security import (
    create_access_token,
    create_refresh_token,
    hash_value,
    verify_password,
)

# TODO: вынести security в отдельный сервис, сделать порт в апп, а реализацию в инфру


class AuthenticateUserUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, credentials: LoginDTO) -> User | None:
        async with self._uow as uow:
            user = await uow.users.get_by_email(credentials.email)
            if user is None or not user.is_active:
                return None
            if not verify_password(credentials.password, user.hashed_password):
                return None
            return user


class IssueTokenPairUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, user_id: UUID) -> TokenPairDTO | None:
        async with self._uow as uow:
            user = await uow.users.get(user_id)
            if user is None or not user.is_active:
                return None

            jti = uuid4()
            refresh_token = create_refresh_token(
                RefreshTokenDataDTO(user_id=user.id, jti=jti)
            )
            access_token = create_access_token(
                AccessTokenDataDTO(user_id=user.id, role=user.role)
            )

            await uow.refresh_tokens.add_token(
                jti=jti,
                user_id=user.id,
                token_hash=hash_value(refresh_token.token),
                expires_at=refresh_token.expiration_time,
            )
            await uow.commit()
            return TokenPairDTO(
                access_token=access_token.token,
                refresh_token=refresh_token.token,
            )


class RefreshTokenPairUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, refresh_token_raw: str, token_data: RefreshTokenDataDTO
    ) -> TokenPairDTO | None:
        async with self._uow as uow:
            stored_token = await uow.refresh_tokens.get_by_jti(token_data.jti)
            if stored_token is None:
                await uow.commit()
                return None

            if stored_token.revoked_at is not None:
                return None
            if stored_token.is_expired():
                await uow.refresh_tokens.revoke(stored_token.jti)
                await uow.commit()
                return None
            if not verify_password(refresh_token_raw, stored_token.token_hash):
                return None

            user = await uow.users.get(stored_token.user_id)
            if user is None or not user.is_active:
                return None

            await uow.refresh_tokens.revoke(stored_token.jti)

            new_jti = uuid4()
            new_refresh_token = create_refresh_token(
                RefreshTokenDataDTO(user_id=user.id, jti=new_jti)
            )
            new_access_token = create_access_token(
                AccessTokenDataDTO(user_id=user.id, role=user.role)
            )
            await uow.refresh_tokens.add_token(
                jti=new_jti,
                user_id=user.id,
                token_hash=hash_value(new_refresh_token.token),
                expires_at=new_refresh_token.expiration_time,
            )
            await uow.commit()

            return TokenPairDTO(
                access_token=new_access_token.token,
                refresh_token=new_refresh_token.token,
            )


class LogoutUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, token_data: RefreshTokenDataDTO) -> None:
        async with self._uow as uow:
            await uow.refresh_tokens.revoke(token_data.jti)
            await uow.commit()


class GetCurrentUserUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, current_user: CurrentUserDTO) -> CurrentUserDetailsDTO:
        async with self._uow as uow:
            user = await uow.users.get(current_user.user_id)
            if user is None:
                raise NotFoundError(f"User {current_user.user_id} not found")
            return CurrentUserDetailsDTO(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
            )


def _user_to_admin_dto(user: User) -> UserAdminDTO:
    return UserAdminDTO(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


class ListUsersUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, limit: int, offset: int
    ) -> PaginatedItemsDTO[UserAdminDTO]:
        async with self._uow as uow:
            users = await uow.users.get_list(limit=limit, offset=offset)
            total = await uow.users.count()
            return PaginatedItemsDTO[UserAdminDTO](
                items=[_user_to_admin_dto(user) for user in users],
                total=total,
                limit=limit,
                offset=offset,
            )


class CreateUserUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UserCreateDTO) -> UserAdminDTO:
        async with self._uow as uow:
            existing = await uow.users.get_by_email(command.email)
            if existing is not None:
                raise ConflictError(f"User with email {command.email} already exists")
            user = User(
                id=uuid4(),
                email=command.email,
                hashed_password=hash_value(command.password),
                role=command.role,
                is_active=True,
            )
            await uow.users.add(user)
            await uow.commit()
            return _user_to_admin_dto(user)


class UpdateUserRoleUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        user_id: UUID,
        command: UserRoleUpdateDTO,
        *,
        actor_user_id: UUID,
    ) -> UserAdminDTO:
        async with self._uow as uow:
            if user_id == actor_user_id:
                raise ConflictError("Cannot change own role")
            user = await uow.users.get(user_id)
            if user is None:
                raise NotFoundError(f"User {user_id} not found")
            user.role = command.role
            await uow.users.add(user)
            await uow.commit()
            return _user_to_admin_dto(user)


class UpdateUserStatusUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        user_id: UUID,
        command: UserStatusUpdateDTO,
        *,
        actor_user_id: UUID,
    ) -> UserAdminDTO:
        async with self._uow as uow:
            if user_id == actor_user_id and not command.is_active:
                raise ConflictError("Cannot deactivate own account")
            user = await uow.users.get(user_id)
            if user is None:
                raise NotFoundError(f"User {user_id} not found")
            user.is_active = command.is_active
            await uow.users.add(user)
            await uow.commit()
            return _user_to_admin_dto(user)
