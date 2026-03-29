from __future__ import annotations

from dataclasses import dataclass

from competency_system.application.ports.health import HealthCheckPort


@dataclass(frozen=True)
class HealthCheckResult:
    status: str
    database: str


class HealthCheckUseCase:
    def __init__(self, health_check_port: HealthCheckPort) -> None:
        self._health_check_port = health_check_port

    async def execute(self) -> HealthCheckResult:
        database_ok = await self._health_check_port.check_database()
        return HealthCheckResult(
            status="ok",
            database="ok" if database_ok else "unavailable",
        )
