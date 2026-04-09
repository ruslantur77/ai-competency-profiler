from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from competency_system.presentation.api import dependencies

pytestmark = pytest.mark.contract


def _build_app(secret: str) -> FastAPI:
    app = FastAPI()
    app.state.testing_system_webhook_secret = secret

    @app.post(
        "/webhook",
        dependencies=[Depends(dependencies.verify_testing_system_webhook_secret)],
    )
    def webhook() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_webhook_secret_verification() -> None:
    app = _build_app("shared-secret")

    with TestClient(app) as client:
        accepted = client.post(
            "/webhook",
            headers={"X-Webhook-Secret": "shared-secret"},
        )
        rejected = client.post("/webhook")

    assert accepted.status_code == 200
    assert accepted.json() == {"ok": True}
    assert rejected.status_code == 401
