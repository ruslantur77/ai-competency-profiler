from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from competency_system.domain.entities import User
from competency_system.domain.value_objects.enums import UserRole
from competency_system.infrastructure.persistence.models import Base
from competency_system.infrastructure.persistence.repositories import UserRepository
from competency_system.infrastructure.security import hash_value
from competency_system.presentation.api.dependencies import get_session_factory
from competency_system.presentation.api.main import app


def _make_session_factory(
    database_path: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    async def _setup() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        return engine, async_sessionmaker(engine, expire_on_commit=False)

    return asyncio.run(_setup())


def _seed_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    password: str,
    role: UserRole,
) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            repo = UserRepository(session)
            await repo.add(
                User(
                    email=email,
                    hashed_password=hash_value(password),
                    role=role,
                    is_active=True,
                )
            )
            await session.commit()

    asyncio.run(_seed())


def test_auth_login_refresh_logout_flow(tmp_path: Path) -> None:
    engine, session_factory = _make_session_factory(str(tmp_path / "auth_flow.db"))
    _seed_user(
        session_factory,
        email="admin@example.com",
        password="test-pass",
        role=UserRole.ADMIN,
    )

    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        with TestClient(app) as client:
            login_response = client.post(
                "/api/v1/auth/login",
                data={"username": "admin@example.com", "password": "test-pass"},
            )
            assert login_response.status_code == 200
            payload = login_response.json()
            assert payload["token_type"] == "bearer"
            assert payload["access_token"]
            assert "refresh_token" in login_response.cookies

            refresh_response = client.post("/api/v1/auth/refresh")
            assert refresh_response.status_code == 200
            refreshed_payload = refresh_response.json()
            assert refreshed_payload["token_type"] == "bearer"
            assert refreshed_payload["access_token"]

            logout_response = client.post("/api/v1/auth/logout")
            assert logout_response.status_code == 204

            refresh_after_logout = client.post("/api/v1/auth/refresh")
            assert refresh_after_logout.status_code == 401
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_protected_route_rejects_missing_bearer() -> None:
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/vacancies/{uuid4()}/suggestions/decision",
            json={"suggestion_id": str(uuid4()), "status": "approved"},
        )

    assert response.status_code == 401
