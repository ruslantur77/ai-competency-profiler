from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from competency_system.infrastructure.settings import get_settings
from competency_system.presentation.api import dependencies

pytestmark = pytest.mark.contract


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.post(
        "/webhook",
        dependencies=[Depends(dependencies.verify_testing_system_webhook_secret)],
    )
    def webhook() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_webhook_secret_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TESTING_SYSTEM_WEBHOOK_SECRET", "shared-secret")
    get_settings.cache_clear()

    app = _build_app()

    try:
        with TestClient(app) as client:
            accepted = client.post(
                "/webhook",
                headers={"X-Webhook-Secret": "shared-secret"},
            )
            rejected = client.post("/webhook")
    finally:
        get_settings.cache_clear()

    assert accepted.status_code == 200
    assert accepted.json() == {"ok": True}
    assert rejected.status_code == 401
