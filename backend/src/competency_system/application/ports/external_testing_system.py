from __future__ import annotations

from datetime import datetime
from typing import Protocol

from competency_system.application.dtos.external_system import ExternalTaskRecord


class ExternalTestingSystemGateway(Protocol):
    async def list_tasks(
        self, start: datetime, end: datetime, force: bool = False
    ) -> list[ExternalTaskRecord]: ...
