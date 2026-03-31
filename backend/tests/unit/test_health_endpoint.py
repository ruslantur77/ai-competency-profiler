from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from competency_system.application.use_cases.health import HealthCheckResult
from competency_system.presentation.api.dependencies import get_health_check_use_case
from competency_system.presentation.api.main import app

pytestmark = pytest.mark.unit


class _FakeHealthUseCase:
    async def execute(self) -> HealthCheckResult:
        return HealthCheckResult(status="ok", database="ok")


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    app.dependency_overrides[get_health_check_use_case] = lambda: _FakeHealthUseCase()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/health", headers={"X-Request-ID": "request-123"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["X-Request-ID"] == "request-123"
