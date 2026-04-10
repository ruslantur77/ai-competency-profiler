from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from competency_system.application.dtos import ExternalTaskRecord
from competency_system.application.ports.external_testing_system import (
    ExternalTestingSystemGateway,
)
from competency_system.domain.value_objects.enums import TaskType


class HTTPTestingSystemGateway(ExternalTestingSystemGateway):
    def __init__(self, *, base_url: str, api_token: str) -> None:
        self._base_url = base_url
        self._api_token = api_token
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._build_headers(),
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        return headers

    async def list_tasks(
        self, start: datetime, end: datetime, force: bool = False
    ) -> list[ExternalTaskRecord]:
        response = await self._client.get(
            "/external/tasks",
            params={
                "start": self._to_utc_iso(start),
                "end": self._to_utc_iso(end),
                "force": str(force).lower(),
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Expected list response from testing system")
        return [self._to_record(item) for item in payload]

    def _to_utc_iso(self, value: datetime) -> str:
        normalized = value.astimezone(UTC)
        return normalized.isoformat().replace("+00:00", "Z")

    def _to_record(self, payload: dict[str, Any]) -> ExternalTaskRecord:
        return ExternalTaskRecord(
            external_id=str(payload["external_id"]),
            title=str(payload["title"]),
            description=str(payload.get("description", "")),
            type=TaskType(str(payload.get("type", "CODE")).lower()),
            tags=[str(tag) for tag in payload.get("tags", [])],
        )
