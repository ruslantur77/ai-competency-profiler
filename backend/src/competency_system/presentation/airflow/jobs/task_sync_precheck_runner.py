from __future__ import annotations

import asyncio

from competency_system.infrastructure.database import (
    create_engine_and_session_factory,
    ping_database,
)
from competency_system.infrastructure.logging import configure_logging, get_logger
from competency_system.presentation.airflow.jobs.task_sync_runtime import (
    TaskSyncRunnerConfig,
    load_runner_config,
)

logger = get_logger(__name__)


def _load_runner_config() -> TaskSyncRunnerConfig:
    return load_runner_config()


async def _run_precheck(config: TaskSyncRunnerConfig) -> None:
    configure_logging(log_level=config.log_level, environment=config.environment)
    db_engine, session_factory = create_engine_and_session_factory(
        database_url=config.database_url,
        debug=config.debug,
    )

    try:
        async with session_factory() as session:
            await ping_database(session)
    finally:
        await db_engine.dispose()


def main() -> None:
    config = _load_runner_config()
    asyncio.run(_run_precheck(config))
    logger.info("task_sync_runtime_precheck_passed")


if __name__ == "__main__":
    main()
