from __future__ import annotations

import os

import pytest

from competency_system.infrastructure.settings import get_settings
from competency_system.presentation.api.main import app
from tests.factories.dto import ApiDTOFactory


@pytest.fixture(autouse=True)
def contract_environment_guard() -> None:
    tracked_keys = ("API_KEY", "SECRET_KEY")
    previous = {key: os.environ.get(key) for key in tracked_keys}

    os.environ["API_KEY"] = "contract-test-api-key"
    os.environ["SECRET_KEY"] = "contract-test-secret-key"
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


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def api_dto_factory() -> ApiDTOFactory:
    return ApiDTOFactory()
