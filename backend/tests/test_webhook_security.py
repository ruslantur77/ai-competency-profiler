from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from competency_system.infrastructure.settings import Settings
from competency_system.presentation.api import dependencies


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
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(testing_system_webhook_secret="shared-secret"),
    )

    app = _build_app()

    with TestClient(app) as client:
        accepted = client.post(
            "/webhook",
            headers={"X-Webhook-Secret": "shared-secret"},
        )
        rejected = client.post("/webhook")

    assert accepted.status_code == 200
    assert accepted.json() == {"ok": True}
    assert rejected.status_code == 401
