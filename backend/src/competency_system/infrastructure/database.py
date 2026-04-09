from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_async_db_engine(*, database_url: str, debug: bool) -> AsyncEngine:
    return create_async_engine(
        database_url,
        echo=debug,
        pool_pre_ping=True,
    )


def create_session_factory(
    *,
    database_url: str,
    debug: bool,
) -> async_sessionmaker[AsyncSession]:
    engine = create_async_db_engine(database_url=database_url, debug=debug)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_engine_and_session_factory(
    *,
    database_url: str,
    debug: bool,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_db_engine(database_url=database_url, debug=debug)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def ping_database(session: AsyncSession) -> None:
    await session.execute(text("SELECT 1"))
