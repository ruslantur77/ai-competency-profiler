from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.domain.entities import User
from competency_system.infrastructure.persistence.models import RefreshTokenOrm
from competency_system.infrastructure.persistence.repositories import (
    RefreshTokenRepository,
    UserRepository,
)

pytestmark = pytest.mark.integration_repo


async def test_refresh_token_repository_flow_and_constraints(
    pg_session: AsyncSession,
) -> None:
    user_repo = UserRepository(pg_session)
    repo = RefreshTokenRepository(pg_session)

    user = User(email="tokens@example.com", hashed_password="hashed")
    await user_repo.add(user)

    active_jti = uuid4()
    await repo.add_token(
        jti=active_jti,
        user_id=user.id,
        token_hash="active-token-hash",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    expired_jti = uuid4()
    await repo.add_token(
        jti=expired_jti,
        user_id=user.id,
        token_hash="expired-token-hash",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    await pg_session.commit()

    active = await repo.get_by_jti(active_jti)
    assert active is not None

    expired = await repo.get_by_jti(expired_jti)
    assert expired is None

    expired_row = await pg_session.get(RefreshTokenOrm, expired_jti)
    assert expired_row is not None
    assert expired_row.revoked_at is not None

    await repo.revoke(active_jti)
    await repo.revoke(active_jti)
    await pg_session.commit()

    revoked = await pg_session.get(RefreshTokenOrm, active_jti)
    assert revoked is not None
    assert revoked.revoked_at is not None

    await repo.delete(active_jti)
    await pg_session.commit()

    assert await repo.get_by_jti(active_jti) is None

    await repo.add_token(
        jti=uuid4(),
        user_id=user.id,
        token_hash="expired-token-hash",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    with pytest.raises(IntegrityError):
        await pg_session.flush()


async def test_refresh_token_cascade_on_user_delete(pg_session: AsyncSession) -> None:
    user_repo = UserRepository(pg_session)
    repo = RefreshTokenRepository(pg_session)

    user = User(email="cascade@example.com", hashed_password="hashed")
    await user_repo.add(user)

    jti = uuid4()
    await repo.add_token(
        jti=jti,
        user_id=user.id,
        token_hash="cascade-token",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await pg_session.commit()

    await user_repo.delete(user.id)
    await pg_session.commit()

    row = await pg_session.get(RefreshTokenOrm, jti)
    assert row is None
