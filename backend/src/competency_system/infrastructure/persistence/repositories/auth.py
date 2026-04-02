from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

from competency_system.application.ports.repositories import (
    RefreshTokenRepository as IRefreshTokenRepository,
)
from competency_system.application.ports.repositories import (
    UserRepository as IUserRepository,
)
from competency_system.domain.entities import RefreshToken, User
from competency_system.infrastructure.persistence.mappers import (
    refresh_token_from_orm,
    refresh_token_to_orm,
    user_from_orm,
    user_to_orm,
)
from competency_system.infrastructure.persistence.models import RefreshTokenOrm, UserOrm
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
)


class UserRepository(SQLAlchemyRepository[User, UserOrm, None], IUserRepository):
    model = UserOrm

    async def get_by_email(self, email: str, *, include: None = None) -> User | None:
        statement = (
            select(UserOrm)
            .where(UserOrm.email == email)
            .options(*self.load_options(include))
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: UserOrm) -> User:
        return user_from_orm(model)

    def to_model(self, entity: User) -> UserOrm:
        return user_to_orm(entity)


class RefreshTokenRepository(
    SQLAlchemyRepository[RefreshToken, RefreshTokenOrm, None], IRefreshTokenRepository
):
    model = RefreshTokenOrm

    async def add_token(
        self,
        *,
        jti: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        token = RefreshTokenOrm(
            jti=jti,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self._session.merge(token)

    async def get_by_jti(
        self,
        jti: UUID,
        *,
        include: None = None,
    ) -> RefreshToken | None:
        statement = select(RefreshTokenOrm).where(RefreshTokenOrm.jti == jti)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        token = self.to_domain(model)
        if token.expires_at <= datetime.now(UTC):
            await self.revoke(token.jti)
            return None
        return token

    async def revoke(self, jti: UUID) -> None:
        statement = (
            update(RefreshTokenOrm)
            .where(RefreshTokenOrm.jti == jti)
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.execute(statement)
        await self._session.flush()

    def to_domain(self, model: RefreshTokenOrm) -> RefreshToken:
        return refresh_token_from_orm(model)

    def to_model(self, entity: RefreshToken) -> RefreshTokenOrm:
        return refresh_token_to_orm(entity)
