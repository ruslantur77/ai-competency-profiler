from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.presentation.api.dependencies import get_uow
from competency_system.presentation.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app.dependency_overrides[get_uow] = lambda: SQLAlchemyUnitOfWork(
        sqlite_session_factory
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/health", headers={"X-Request-ID": "request-123"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["X-Request-ID"] == "request-123"
