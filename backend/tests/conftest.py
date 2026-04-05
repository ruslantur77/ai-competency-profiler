from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

import pytest

from competency_system.infrastructure.settings import get_settings


@pytest.fixture(autouse=True)
def test_environment_guard() -> None:
    default_test_env = {
        "API_KEY": "test-api-key",
        "BASE_URL": "https://example.invalid/api/v1",
        "MODEL": "test-model",
        "SECRET_KEY": "test-secret-key",
        "BOOTSTRAP_ADMIN_EMAIL": "",
        "BOOTSTRAP_ADMIN_PASSWORD": "",
        "TESTING_SYSTEM_WEBHOOK_SECRET": "",
    }
    tracked_keys = tuple(default_test_env.keys())
    previous = {key: os.environ.get(key) for key in tracked_keys}

    for key, value in default_test_env.items():
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


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def fixed_uuid() -> UUID:
    return UUID("12345678-1234-5678-1234-567812345678")
