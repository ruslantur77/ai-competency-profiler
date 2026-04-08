from __future__ import annotations

import pytest

from competency_system.presentation.airflow.jobs.task_sync_runner import _parse_payload


@pytest.mark.unit
def test_task_sync_runner_parse_payload_success() -> None:
    payload = _parse_payload("2026-04-09T00:00:00Z", "2026-04-09T01:00:00Z")

    assert payload.start.isoformat() == "2026-04-09T00:00:00+00:00"
    assert payload.end.isoformat() == "2026-04-09T01:00:00+00:00"


@pytest.mark.unit
def test_task_sync_runner_parse_payload_rejects_non_utc() -> None:
    with pytest.raises(ValueError, match="Datetime must be in UTC"):
        _parse_payload("2026-04-09T03:00:00+03:00", "2026-04-09T04:00:00+03:00")


@pytest.mark.unit
def test_task_sync_runner_parse_payload_rejects_invalid_range() -> None:
    with pytest.raises(ValueError, match="'end' must be greater than 'start'"):
        _parse_payload("2026-04-09T01:00:00Z", "2026-04-09T01:00:00Z")
