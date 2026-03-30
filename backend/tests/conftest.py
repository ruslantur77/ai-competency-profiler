from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from competency_system.infrastructure.persistence.models import Base
from competency_system.infrastructure.settings import get_settings


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("integration-db")
    group.addoption(
        "--test-db-url",
        action="store",
        default=None,
        help=(
            "PostgreSQL URL for integration tests. "
            "Example: postgresql://user:pass@127.0.0.1:5432/app"
        ),
    )
    group.addoption("--test-db-host", action="store", default=None)
    group.addoption("--test-db-port", action="store", default=None)
    group.addoption("--test-db-name", action="store", default=None)
    group.addoption("--test-db-user", action="store", default=None)
    group.addoption("--test-db-pass", action="store", default=None)


@pytest.fixture(autouse=True)
def test_environment_guard() -> None:
    tracked_keys = (
        "BOOTSTRAP_ADMIN_EMAIL",
        "BOOTSTRAP_ADMIN_PASSWORD",
        "TESTING_SYSTEM_WEBHOOK_SECRET",
    )
    previous = {key: os.environ.get(key) for key in tracked_keys}

    os.environ["BOOTSTRAP_ADMIN_EMAIL"] = ""
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = ""
    os.environ["TESTING_SYSTEM_WEBHOOK_SECRET"] = ""
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
async def sqlite_engine(tmp_path: Path) -> AsyncEngine:
    database_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
def sqlite_session_factory(
    sqlite_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(sqlite_engine, expire_on_commit=False)
