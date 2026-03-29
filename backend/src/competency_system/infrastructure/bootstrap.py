from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from competency_system.domain.entities import User
from competency_system.domain.value_objects.enums import UserRole
from competency_system.infrastructure.logging import get_logger
from competency_system.infrastructure.persistence.repositories import UserRepository
from competency_system.infrastructure.security import hash_value
from competency_system.infrastructure.settings import Settings

logger = get_logger(__name__)


async def ensure_bootstrap_admin(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    email = settings.bootstrap_admin_email.strip()
    password = settings.bootstrap_admin_password
    if not email or not password:
        return

    async with session_factory() as session:
        repo = UserRepository(session)
        existing_user = await repo.get_by_email(email)
        if existing_user is not None:
            return

        admin_user = User(
            email=email,
            hashed_password=hash_value(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        await repo.add(admin_user)
        await session.commit()
        logger.info("bootstrap_admin_created", email=email)
