from __future__ import annotations

import pytest

from competency_system.application.ports.health import HealthCheckPort
from competency_system.application.use_cases.health import HealthCheckUseCase

pytestmark = pytest.mark.unit


class HealthyPort(HealthCheckPort):
    async def check_database(self) -> bool:
        return True


class UnhealthyPort(HealthCheckPort):
    async def check_database(self) -> bool:
        return False


async def test_health_use_case_returns_ok_when_database_available() -> None:
    result = await HealthCheckUseCase(HealthyPort()).execute()

    assert result.status == "ok"
    assert result.database == "ok"


async def test_health_use_case_returns_unavailable_when_database_unavailable() -> None:
    result = await HealthCheckUseCase(UnhealthyPort()).execute()

    assert result.status == "ok"
    assert result.database == "unavailable"
