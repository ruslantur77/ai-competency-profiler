from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from competency_system.application.ports.uow import UnitOfWork
from competency_system.infrastructure.database import create_engine_and_session_factory
from competency_system.infrastructure.external.testing_system import (
    HTTPTestingSystemGateway,
)
from competency_system.infrastructure.llm.job_queue import InMemoryLLMJobQueue
from competency_system.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMGateway,
)
from competency_system.infrastructure.logging import configure_logging, get_logger
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.infrastructure.settings import Settings, get_settings

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class AirflowRuntime:
    settings: Settings
    db_engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    llm_gateway_client: OpenAICompatibleLLMGateway
    testing_gateway_client: HTTPTestingSystemGateway
    llm_job_queue_client: InMemoryLLMJobQueue

    def uow(self) -> UnitOfWork:
        return SQLAlchemyUnitOfWork(self.session_factory)

    def llm_gateway(self) -> OpenAICompatibleLLMGateway:
        return self.llm_gateway_client

    def testing_gateway(self) -> HTTPTestingSystemGateway:
        return self.testing_gateway_client

    def llm_job_queue(self) -> InMemoryLLMJobQueue:
        return self.llm_job_queue_client

    async def close(self) -> None:
        await self.llm_job_queue_client.close()
        await self.testing_gateway_client.close()
        await self.llm_gateway_client.close()
        await self.db_engine.dispose()


@asynccontextmanager
async def build_runtime() -> AsyncIterator[AirflowRuntime]:
    settings = get_settings()
    configure_logging(settings)
    db_engine, session_factory = create_engine_and_session_factory(settings)
    runtime = AirflowRuntime(
        settings=settings,
        db_engine=db_engine,
        session_factory=session_factory,
        llm_gateway_client=OpenAICompatibleLLMGateway(settings),
        testing_gateway_client=HTTPTestingSystemGateway(settings),
        llm_job_queue_client=InMemoryLLMJobQueue(),
    )
    try:
        yield runtime
    finally:
        await runtime.close()


def run_async[T](factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(factory())


def run_logged_async[T](
    task_name: str,
    factory: Callable[[AirflowRuntime], Coroutine[Any, Any, T]],
) -> T:
    logger = get_logger(__name__).bind(component="airflow", task_name=task_name)
    started_at = perf_counter()
    logger.info("task_started")

    async def _execute() -> T:
        async with build_runtime() as runtime:
            return await factory(runtime)

    try:
        result = asyncio.run(_execute())
    except Exception:
        duration_ms = round((perf_counter() - started_at) * 1000.0, 2)
        logger.exception("task_failed", duration_ms=duration_ms)
        raise

    duration_ms = round((perf_counter() - started_at) * 1000.0, 2)
    logger.info("task_finished", duration_ms=duration_ms)
    return result
