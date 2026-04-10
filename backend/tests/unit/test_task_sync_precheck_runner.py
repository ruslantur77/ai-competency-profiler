from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import competency_system.presentation.airflow.jobs.task_sync_precheck_runner as precheck

pytestmark = pytest.mark.unit


class _SessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class _SessionFactory:
    def __init__(self, session: object) -> None:
        self._session = session

    def __call__(self) -> _SessionContext:
        return _SessionContext(self._session)


def test_task_sync_precheck_runner_load_config_rejects_missing_database_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASS", raising=False)

    with pytest.raises(ValueError, match="Database configuration is incomplete"):
        precheck._load_runner_config()


def test_task_sync_precheck_runner_run_precheck_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = precheck.TaskSyncRunnerConfig(
        debug=False,
        environment="test",
        log_level="INFO",
        database_url="postgresql+asyncpg://user:pass@db:5432/app",
        testing_system_base_url="http://localhost:9000",
        testing_system_api_token="",
        llm_queue_backend="inmemory",
        redis_host="127.0.0.1",
        redis_port=6379,
        redis_password="",
        celery_queue_name="llm_jobs",
        celery_result_expires_seconds=86400,
    )
    session = object()
    engine = SimpleNamespace(dispose=AsyncMock())
    ping_database = AsyncMock()

    monkeypatch.setattr(
        precheck,
        "create_engine_and_session_factory",
        lambda **_: (engine, _SessionFactory(session)),
    )
    monkeypatch.setattr(precheck, "ping_database", ping_database)

    asyncio.run(precheck._run_precheck(config))

    ping_database.assert_awaited_once_with(session)
    engine.dispose.assert_awaited_once()


def test_task_sync_precheck_runner_run_precheck_disposes_engine_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = precheck.TaskSyncRunnerConfig(
        debug=False,
        environment="test",
        log_level="INFO",
        database_url="postgresql+asyncpg://user:pass@db:5432/app",
        testing_system_base_url="http://localhost:9000",
        testing_system_api_token="",
        llm_queue_backend="inmemory",
        redis_host="127.0.0.1",
        redis_port=6379,
        redis_password="",
        celery_queue_name="llm_jobs",
        celery_result_expires_seconds=86400,
    )
    engine = SimpleNamespace(dispose=AsyncMock())
    ping_database = AsyncMock(side_effect=RuntimeError("db unavailable"))

    monkeypatch.setattr(
        precheck,
        "create_engine_and_session_factory",
        lambda **_: (engine, _SessionFactory(object())),
    )
    monkeypatch.setattr(precheck, "ping_database", ping_database)

    with pytest.raises(RuntimeError, match="db unavailable"):
        asyncio.run(precheck._run_precheck(config))

    engine.dispose.assert_awaited_once()
