from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
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


@dataclass(frozen=True)
class TestDatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    async_url: str
    sync_url: str

    @classmethod
    def from_pytest_config(cls, config: pytest.Config) -> TestDatabaseConfig:
        url_raw = _first_non_empty(
            _option(config, "test_db_url"),
            os.environ.get("TEST_DB_URL"),
            os.environ.get("TEST_DATABASE_URL"),
        )
        if url_raw:
            return _from_url(url_raw)

        host = _first_non_empty(
            _option(config, "test_db_host"),
            os.environ.get("TEST_DB_HOST"),
            os.environ.get("DB_HOST"),
            "127.0.0.1",
        )
        port_raw = _first_non_empty(
            _option(config, "test_db_port"),
            os.environ.get("TEST_DB_PORT"),
            os.environ.get("DB_PORT"),
            "5432",
        )
        name = _first_non_empty(
            _option(config, "test_db_name"),
            os.environ.get("TEST_DB_NAME"),
            os.environ.get("DB_NAME"),
            "app",
        )
        user = _first_non_empty(
            _option(config, "test_db_user"),
            os.environ.get("TEST_DB_USER"),
            os.environ.get("DB_USER"),
            "app",
        )
        password = _first_non_empty(
            _option(config, "test_db_pass"),
            os.environ.get("TEST_DB_PASS"),
            os.environ.get("DB_PASS"),
            "app",
        )
        port = int(port_raw)
        async_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
        sync_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        return cls(
            host=host,
            port=port,
            name=name,
            user=user,
            password=password,
            async_url=async_url,
            sync_url=sync_url,
        )

    @property
    def runtime_env(self) -> dict[str, str]:
        return {
            "DB_HOST": self.host,
            "DB_PORT": str(self.port),
            "DB_NAME": self.name,
            "DB_USER": self.user,
            "DB_PASS": self.password,
        }


def _option(config: pytest.Config, name: str) -> str | None:
    value = config.getoption(name)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value is None:
            continue
        stripped = value.strip()
        if stripped:
            return stripped
    return ""


def _from_url(url_raw: str) -> TestDatabaseConfig:
    parsed = make_url(url_raw)
    if not parsed.drivername.startswith("postgresql"):
        msg = (
            "Only PostgreSQL URLs are supported for integration tests. "
            f"Got driver '{parsed.drivername}'."
        )
        raise pytest.UsageError(msg)

    async_url = parsed.set(drivername="postgresql+asyncpg").render_as_string(
        hide_password=False
    )
    sync_url = parsed.set(drivername="postgresql+psycopg2").render_as_string(
        hide_password=False
    )

    host = parsed.host or "127.0.0.1"
    port = int(parsed.port or 5432)
    name = parsed.database or "app"
    user = parsed.username or "app"
    password = parsed.password or "app"

    return TestDatabaseConfig(
        host=host,
        port=port,
        name=name,
        user=user,
        password=password,
        async_url=async_url,
        sync_url=sync_url,
    )


def _test_db_availability_error(config: TestDatabaseConfig) -> str | None:
    engine = create_engine(config.sync_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return (
            "Integration DB connection failed. "
            "Provide test DB credentials via "
            "TEST_DB_URL (or TEST_DATABASE_URL), "
            "or TEST_DB_HOST/TEST_DB_PORT/TEST_DB_NAME/TEST_DB_USER/TEST_DB_PASS, "
            "or pytest options --test-db-url / --test-db-*. "
            "Attempted "
            f"host={config.host} port={config.port} db={config.name} "
            f"user={config.user}. "
            f"Original error: {exc}"
        )
    finally:
        engine.dispose()
    return None


def _prepare_test_database_for_migrations(config: TestDatabaseConfig) -> None:
    engine = create_engine(config.sync_url, pool_pre_ping=True)
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
    db_config = TestDatabaseConfig.from_pytest_config(request.config)
    availability_error = _test_db_availability_error(db_config)
    if availability_error is not None:
        pytest.skip(f"Skipping integration tests: {availability_error}")
    _prepare_test_database_for_migrations(db_config)

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
    db_config = TestDatabaseConfig.from_pytest_config(request.config)
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
