from __future__ import annotations

import pytest

from competency_system.presentation.airflow.jobs.task_sync_runner import (
    _load_runner_config,
    _parse_payload,
)


@pytest.mark.unit
def test_task_sync_runner_parse_payload_success() -> None:
    payload = _parse_payload("2026-04-09T00:00:00Z", "2026-04-09T01:00:00Z", "true")

    assert payload.start.isoformat() == "2026-04-09T00:00:00+00:00"
    assert payload.end.isoformat() == "2026-04-09T01:00:00+00:00"
    assert payload.force is True


@pytest.mark.unit
def test_task_sync_runner_parse_payload_rejects_non_utc() -> None:
    with pytest.raises(ValueError, match="Datetime must be in UTC"):
        _parse_payload(
            "2026-04-09T03:00:00+03:00", "2026-04-09T04:00:00+03:00", "false"
        )


@pytest.mark.unit
def test_task_sync_runner_parse_payload_rejects_invalid_range() -> None:
    with pytest.raises(ValueError, match="'end' must be greater than 'start'"):
        _parse_payload("2026-04-09T01:00:00Z", "2026-04-09T01:00:00Z", "false")


@pytest.mark.unit
def test_task_sync_runner_loads_database_url_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/app")
    config = _load_runner_config()
    assert config.database_url == "postgresql+asyncpg://user:pass@db:5432/app"


@pytest.mark.unit
def test_task_sync_runner_builds_database_url_from_db_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "app")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASS", "pass")

    config = _load_runner_config()
    assert config.database_url == "postgresql+asyncpg://user:pass@db:5432/app"
