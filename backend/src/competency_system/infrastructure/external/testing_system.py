from __future__ import annotations

from typing import Any

import httpx

from competency_system.application.ports.external_testing_system import (
    ExternalTaskRecord,
    ExternalTestingSystemGateway,
)
from competency_system.domain.value_objects.enums import TaskType
from competency_system.infrastructure.settings import Settings, get_settings


class HTTPTestingSystemGateway(ExternalTestingSystemGateway):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = httpx.AsyncClient(
            base_url=self._settings.testing_system_base_url,
            headers=self._build_headers(),
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._settings.testing_system_api_token:
            headers["Authorization"] = f"Bearer {self._settings.testing_system_api_token}"
        return headers

    async def list_tasks(self) -> list[ExternalTaskRecord]:
        response = await self._client.get("/external/tasks")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Expected list response from testing system")
        return [self._to_record(item) for item in payload]

    def _to_record(self, payload: dict[str, Any]) -> ExternalTaskRecord:
        return ExternalTaskRecord(
            external_id=str(payload["external_id"]),
            title=str(payload["title"]),
            description=str(payload.get("description", "")),
            type=TaskType(str(payload.get("type", "CODE")).lower()),
            tags=[str(tag) for tag in payload.get("tags", [])],
        )
