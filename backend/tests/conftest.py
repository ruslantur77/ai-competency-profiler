from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

import pytest

from competency_system.infrastructure.settings import get_settings


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


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def fixed_uuid() -> UUID:
    return UUID("12345678-1234-5678-1234-567812345678")
