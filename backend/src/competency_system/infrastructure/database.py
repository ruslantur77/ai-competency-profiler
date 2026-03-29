from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from competency_system.infrastructure.settings import Settings, get_settings


def create_async_db_engine(settings: Settings | None = None) -> AsyncEngine:
    resolved_settings = settings or get_settings()
    return create_async_engine(
        resolved_settings.database_url,
        echo=resolved_settings.debug,
        pool_pre_ping=True,
    )


def create_session_factory(
    settings: Settings | None = None,
) -> async_sessionmaker[AsyncSession]:
    engine = create_async_db_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_engine_and_session_factory(
    settings: Settings | None = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_db_engine(settings)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def ping_database(session: AsyncSession) -> None:
    await session.execute(text("SELECT 1"))
