from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import UserInclude
from competency_system.domain.entities import User
from competency_system.domain.value_objects.enums import UserRole
from competency_system.infrastructure.persistence.repositories import (
    RefreshTokenRepository,
    UserRepository,
)

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_user_repository_crud_and_uniqueness(pg_session: AsyncSession) -> None:
    user_repo = UserRepository(pg_session)
    token_repo = RefreshTokenRepository(pg_session)

    user = User(
        email="user@example.com",
        hashed_password="hashed",
        role=UserRole.EXPERT,
        is_active=True,
    )
    await user_repo.add(user)
    await pg_session.commit()

    loaded = await user_repo.get(user.id, include={UserInclude.REFRESH_TOKENS})
    assert loaded is not None
    assert loaded.email == "user@example.com"

    by_email = await user_repo.get_by_email(
        "user@example.com",
        include={UserInclude.REFRESH_TOKENS},
    )
    assert by_email is not None
    assert by_email.id == user.id

    await token_repo.add_token(
        jti=uuid4(),
        user_id=user.id,
        token_hash="token-hash-1",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await pg_session.commit()

    user.role = UserRole.ADMIN
    await user_repo.add(user)
    await pg_session.commit()

    updated = await user_repo.get(user.id)
    assert updated is not None
    assert updated.role == UserRole.ADMIN

    with pytest.raises(IntegrityError):
        await user_repo.add(User(email="user@example.com", hashed_password="other"))
