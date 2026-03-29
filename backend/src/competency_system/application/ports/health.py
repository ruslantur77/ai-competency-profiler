from __future__ import annotations

from typing import Protocol


class HealthCheckPort(Protocol):
    async def check_database(self) -> bool: ...
