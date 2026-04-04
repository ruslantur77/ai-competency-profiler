from __future__ import annotations

import pytest

from competency_system.presentation.api.main import app
from tests.factories.dto import ApiDTOFactory


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def api_dto_factory() -> ApiDTOFactory:
    return ApiDTOFactory()
