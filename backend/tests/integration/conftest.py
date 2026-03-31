from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command
from competency_system.infrastructure.persistence.models import Base
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.infrastructure.settings import get_settings
from tests.config import resolve_test_db_config


def _test_db_availability_error(sync_url: str, *, details: str) -> str | None:
    engine = create_engine(sync_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return (
            "Integration DB connection failed. "
            "Provide test DB credentials via TEST_DB_HOST/TEST_DB_PORT/"
            "TEST_DB_NAME/TEST_DB_USER/TEST_DB_PASS, "
            "or pytest options --test-db-* (optionally --test-db-url). "
            f"Attempted {details}. "
            f"Original error: {exc}"
        )
    finally:
        engine.dispose()
    return None


def _prepare_test_database_for_migrations(sync_url: str) -> None:
    engine = create_engine(sync_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(255) NOT NULL PRIMARY KEY
                    )
                    """
                )
            )
    finally:
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def apply_postgres_migrations(request: pytest.FixtureRequest) -> None:
    db_config = resolve_test_db_config(request.config)
    details = (
        f"host={db_config.host} port={db_config.port} "
        f"db={db_config.name} user={db_config.user}"
    )
    availability_error = _test_db_availability_error(
        db_config.sync_url, details=details
    )
    if availability_error is not None:
        pytest.skip(f"Skipping integration tests: {availability_error}")

    _prepare_test_database_for_migrations(db_config.sync_url)

    runtime_env = db_config.runtime_env
    tracked_keys = tuple(runtime_env.keys())
    previous = {key: os.environ.get(key) for key in tracked_keys}
    for key, value in runtime_env.items():
        os.environ[key] = value

    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(root / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
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
async def pg_engine(request: pytest.FixtureRequest) -> AsyncEngine:
    db_config = resolve_test_db_config(request.config)
    engine = create_async_engine(db_config.async_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(pg_engine: AsyncEngine) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    if table_names:
        async with pg_engine.begin() as connection:
            await connection.execute(
                text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
            )
    yield


@pytest.fixture()
def pg_session_factory(
    pg_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(pg_engine, expire_on_commit=False)


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
