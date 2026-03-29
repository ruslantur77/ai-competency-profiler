from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from competency_system.application.ports.health import HealthCheckPort


class SQLAlchemyHealthCheckPort(HealthCheckPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def check_database(self) -> bool:
        async with self._session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
