from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from competency_system.infrastructure.external.testing_system import (
    HTTPTestingSystemGateway,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_http_testing_system_gateway_passes_period_and_auth_header() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            status_code=200,
            json=[
                {
                    "external_id": "task-1",
                    "title": "Task 1",
                    "description": "Desc",
                    "type": "code",
                    "tags": ["api"],
                }
            ],
        )

    gateway = HTTPTestingSystemGateway(
        base_url="http://testing.local",
        api_token="secret",
    )
    await gateway._client.aclose()
    gateway._client = httpx.AsyncClient(
        base_url="http://testing.local",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer secret"},
    )

    start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    end = datetime(2026, 4, 1, 1, 0, tzinfo=UTC)
    result = await gateway.list_tasks(start=start, end=end)
    await gateway.close()

    assert len(result) == 1
    assert captured_request is not None
    assert captured_request.url.path == "/external/tasks"
    assert captured_request.url.params["start"] == "2026-04-01T00:00:00Z"
    assert captured_request.url.params["end"] == "2026-04-01T01:00:00Z"
    assert captured_request.url.params["force"] == "false"
    assert captured_request.headers["Authorization"] == "Bearer secret"
