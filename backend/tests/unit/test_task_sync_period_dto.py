from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from competency_system.application.dtos.task import TaskSyncPeriodDTO

pytestmark = pytest.mark.unit


def test_task_sync_period_accepts_valid_utc_range() -> None:
    payload = TaskSyncPeriodDTO(
        start=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        end=datetime(2026, 4, 1, 1, 0, tzinfo=UTC),
    )
    assert payload.end > payload.start


def test_task_sync_period_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        TaskSyncPeriodDTO(
            start=datetime(2026, 4, 1, 0, 0),
            end=datetime(2026, 4, 1, 1, 0, tzinfo=UTC),
        )


def test_task_sync_period_rejects_non_utc_datetime() -> None:
    plus_three = timezone(timedelta(hours=3))
    with pytest.raises(ValidationError):
        TaskSyncPeriodDTO(
            start=datetime(2026, 4, 1, 0, 0, tzinfo=plus_three),
            end=datetime(2026, 4, 1, 1, 0, tzinfo=UTC),
        )


def test_task_sync_period_rejects_invalid_range() -> None:
    now = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        TaskSyncPeriodDTO(start=now, end=now)
