from __future__ import annotations

from typing import Protocol

from competency_system.application.dtos.external_system import ExternalTaskRecord


class ExternalTestingSystemGateway(Protocol):
    async def list_tasks(self) -> list[ExternalTaskRecord]: ...
