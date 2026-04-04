from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.domain.entities import User
from competency_system.domain.value_objects.enums import UserRole
from competency_system.infrastructure.persistence.repositories import UserRepository

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_user_repository_crud_and_uniqueness(pg_session: AsyncSession) -> None:
    repo = UserRepository(pg_session)

    user = User(
        email="user@example.com",
        hashed_password="hashed",
        role=UserRole.EXPERT,
        is_active=True,
    )
    await repo.add(user)
    await pg_session.commit()

    loaded = await repo.get(user.id)
    assert loaded is not None
    assert loaded.email == "user@example.com"

    by_email = await repo.get_by_email("user@example.com")
    assert by_email is not None
    assert by_email.id == user.id

    user.role = UserRole.ADMIN
    await repo.add(user)
    await pg_session.commit()

    updated = await repo.get(user.id)
    assert updated is not None
    assert updated.role == UserRole.ADMIN

    with pytest.raises(IntegrityError):
        await repo.add(User(email="user@example.com", hashed_password="other"))
