from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from competency_system.infrastructure.persistence.models import Base
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.infrastructure.settings import get_settings
from tests.config import ResolvedTestDBConfig, resolve_test_db_config


@pytest.fixture(scope="session")
def event_loop() -> Any:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


def _assert_test_db_available(db_config: ResolvedTestDBConfig) -> None:
    engine = create_engine(db_config.sync_url, pool_pre_ping=True)
    details = (
        f"host={db_config.host} port={db_config.port} "
        f"db={db_config.name} user={db_config.user}"
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        message = (
            "Integration DB connection failed. "
            "Set TEST_DB_HOST/TEST_DB_PORT/TEST_DB_NAME/TEST_DB_USER/TEST_DB_PASS. "
            f"Attempted {details}. Original error: {exc}"
        )
        raise RuntimeError(message) from exc
    finally:
        engine.dispose()


def _prepare_test_database(sync_url: str) -> None:
    engine = create_engine(sync_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND pid <> pg_backend_pid();
            """)
            )

            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            Base.metadata.create_all(bind=connection)
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def db_config() -> ResolvedTestDBConfig:
    return resolve_test_db_config()


@pytest.fixture(scope="session", autouse=True)
def prepare_postgres_schema(db_config: ResolvedTestDBConfig) -> None:
    _assert_test_db_available(db_config)
    _prepare_test_database(db_config.sync_url)

    runtime_env = db_config.runtime_env
    tracked_keys = tuple(runtime_env.keys())
    previous = {key: os.environ.get(key) for key in tracked_keys}
    for key, value in runtime_env.items():
        os.environ[key] = value

    get_settings.cache_clear()
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


@pytest_asyncio.fixture()
async def pg_engine(db_config: ResolvedTestDBConfig) -> AsyncEngine:
    engine = create_async_engine(db_config.async_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def pg_connection(pg_engine: AsyncEngine) -> AsyncConnection:
    async with pg_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


@pytest.fixture()
def pg_session_factory(
    pg_connection: AsyncConnection,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=pg_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest_asyncio.fixture()
async def pg_session(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncSession:
    async with pg_session_factory() as session:
        yield session


@pytest.fixture()
def uow_factory(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> Any:
    def _factory() -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(pg_session_factory)

    return _factory
