from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class TestDBSettings(BaseSettings):
    TEST_DB_HOST: str
    TEST_DB_PORT: int
    TEST_DB_NAME: str
    TEST_DB_USER: str
    TEST_DB_PASS: str

    model_config = SettingsConfigDict(env_file="tests/.env.test", extra="ignore")

    @property
    def async_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.TEST_DB_USER}:{self.TEST_DB_PASS}@"
            f"{self.TEST_DB_HOST}:{self.TEST_DB_PORT}/{self.TEST_DB_NAME}"
        )

    @property
    def sync_url(self) -> str:
        return (
            "postgresql+psycopg2://"
            f"{self.TEST_DB_USER}:{self.TEST_DB_PASS}@"
            f"{self.TEST_DB_HOST}:{self.TEST_DB_PORT}/{self.TEST_DB_NAME}"
        )

    @property
    def runtime_env(self) -> dict[str, str]:
        return {
            "DB_HOST": self.TEST_DB_HOST,
            "DB_PORT": str(self.TEST_DB_PORT),
            "DB_NAME": self.TEST_DB_NAME,
            "DB_USER": self.TEST_DB_USER,
            "DB_PASS": self.TEST_DB_PASS,
        }


@dataclass(frozen=True)
class ResolvedTestDBConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    async_url: str
    sync_url: str

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


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def resolve_test_db_config(pytest_config: pytest.Config) -> ResolvedTestDBConfig:
    raw_url = _first_non_empty(
        _option(pytest_config, "test_db_url"),
        os.environ.get("TEST_DB_URL"),
        os.environ.get("TEST_DATABASE_URL"),
    )
    if raw_url is not None:
        parsed = make_url(raw_url)
        if not parsed.drivername.startswith("postgresql"):
            msg = (
                "Only PostgreSQL URLs are supported for integration tests. "
                f"Got driver '{parsed.drivername}'."
            )
            raise pytest.UsageError(msg)
        host = parsed.host or "127.0.0.1"
        port = int(parsed.port or 5432)
        name = parsed.database or "app"
        user = parsed.username or "app"
        password = parsed.password or "app"
    else:
        settings = TestDBSettings()
        host = (
            _first_non_empty(
                _option(pytest_config, "test_db_host"),
                os.environ.get("TEST_DB_HOST"),
                settings.TEST_DB_HOST,
            )
            or settings.TEST_DB_HOST
        )
        port = int(
            _first_non_empty(
                _option(pytest_config, "test_db_port"),
                os.environ.get("TEST_DB_PORT"),
                str(settings.TEST_DB_PORT),
            )
            or settings.TEST_DB_PORT
        )
        name = (
            _first_non_empty(
                _option(pytest_config, "test_db_name"),
                os.environ.get("TEST_DB_NAME"),
                settings.TEST_DB_NAME,
            )
            or settings.TEST_DB_NAME
        )
        user = (
            _first_non_empty(
                _option(pytest_config, "test_db_user"),
                os.environ.get("TEST_DB_USER"),
                settings.TEST_DB_USER,
            )
            or settings.TEST_DB_USER
        )
        password = (
            _first_non_empty(
                _option(pytest_config, "test_db_pass"),
                os.environ.get("TEST_DB_PASS"),
                settings.TEST_DB_PASS,
            )
            or settings.TEST_DB_PASS
        )

    async_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
    sync_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return ResolvedTestDBConfig(
        host=host,
        port=port,
        name=name,
        user=user,
        password=password,
        async_url=async_url,
        sync_url=sync_url,
    )
