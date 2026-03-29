from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from competency_system.application.dtos.auth import (
    AccessTokenDataDTO,
    LoginDTO,
    RefreshTokenDataDTO,
    TokenPairDTO,
)
from competency_system.application.ports.repositories import (
    RefreshTokenRepository,
    UserRepository,
)
from competency_system.domain.entities import User
from competency_system.infrastructure.security import (
    create_access_token,
    create_refresh_token,
    hash_value,
    verify_password,
)


class AuthenticateUserUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, credentials: LoginDTO) -> User | None:
        user = await self._user_repo.get_by_email(credentials.email)
        if user is None or not user.is_active:
            return None
        if not verify_password(credentials.password, user.hashed_password):
            return None
        return user


class IssueTokenPairUseCase:
    def __init__(
        self,
        *,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo

    async def execute(self, *, user_id: UUID) -> TokenPairDTO | None:
        user = await self._user_repo.get(user_id)
        if user is None or not user.is_active:
            return None

        jti = uuid4()
        refresh_token = create_refresh_token(
            RefreshTokenDataDTO(user_id=user.id, jti=jti)
        )
        access_token = create_access_token(
            AccessTokenDataDTO(user_id=user.id, role=user.role)
        )

        await self._refresh_token_repo.add_token(
            jti=jti,
            user_id=user.id,
            token_hash=hash_value(refresh_token.token),
            expires_at=refresh_token.expiration_time,
        )
        return TokenPairDTO(
            access_token=access_token.token,
            refresh_token=refresh_token.token,
        )


class RefreshTokenPairUseCase:
    def __init__(
        self,
        *,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo

    async def execute(
        self, *, refresh_token_raw: str, token_data: RefreshTokenDataDTO
    ) -> TokenPairDTO | None:
        stored_token = await self._refresh_token_repo.get_by_jti(token_data.jti)
        if stored_token is None:
            return None

        if stored_token.revoked_at is not None:
            return None
        if stored_token.expires_at <= datetime.now(UTC):
            await self._refresh_token_repo.revoke(stored_token.jti)
            return None
        if not verify_password(refresh_token_raw, stored_token.token_hash):
            return None

        user = await self._user_repo.get(stored_token.user_id)
        if user is None or not user.is_active:
            return None

        await self._refresh_token_repo.revoke(stored_token.jti)

        new_jti = uuid4()
        new_refresh_token = create_refresh_token(
            RefreshTokenDataDTO(user_id=user.id, jti=new_jti)
        )
        new_access_token = create_access_token(
            AccessTokenDataDTO(user_id=user.id, role=user.role)
        )
        await self._refresh_token_repo.add_token(
            jti=new_jti,
            user_id=user.id,
            token_hash=hash_value(new_refresh_token.token),
            expires_at=new_refresh_token.expiration_time,
        )

        return TokenPairDTO(
            access_token=new_access_token.token,
            refresh_token=new_refresh_token.token,
        )


class LogoutUseCase:
    def __init__(self, refresh_token_repo: RefreshTokenRepository) -> None:
        self._refresh_token_repo = refresh_token_repo

    async def execute(self, token_data: RefreshTokenDataDTO) -> None:
        await self._refresh_token_repo.revoke(token_data.jti)
