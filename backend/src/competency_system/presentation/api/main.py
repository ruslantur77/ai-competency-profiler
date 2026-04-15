from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from competency_system.application.errors import ApplicationError
from competency_system.infrastructure.bootstrap import ensure_bootstrap_admin
from competency_system.infrastructure.database import create_engine_and_session_factory
from competency_system.infrastructure.external.testing_system import (
    HTTPTestingSystemGateway,
)
from competency_system.infrastructure.llm.job_queue import InMemoryLLMJobQueue
from competency_system.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMGateway,
)
from competency_system.infrastructure.logging import configure_logging, get_logger
from competency_system.infrastructure.settings import LLMQueueBackend, get_settings
from competency_system.presentation.api.exception_handlers import (
    application_exception_handler,
    unexpected_exception_handler,
)
from competency_system.presentation.api.middleware import (
    request_observability_middleware,
)
from competency_system.presentation.api.routes.admin_tasks import (
    router as admin_tasks_router,
)
from competency_system.presentation.api.routes.admin_users import (
    router as admin_users_router,
)
from competency_system.presentation.api.routes.auth import router as auth_router
from competency_system.presentation.api.routes.candidates import (
    router as candidates_router,
)
from competency_system.presentation.api.routes.health import router as health_router
from competency_system.presentation.api.routes.ranking import router as ranking_router
from competency_system.presentation.api.routes.tasks import router as tasks_router
from competency_system.presentation.api.routes.tasks import webhook_router
from competency_system.presentation.api.routes.vacancies import (
    router as vacancies_router,
)
from competency_system.presentation.api.runtime_config import (
    AuthCookieConfig,
    RebuildTaskMappingConfig,
)

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    db_engine, session_factory = create_engine_and_session_factory(
        database_url=settings.database_url,
        debug=settings.debug,
    )
    llm_gateway = OpenAICompatibleLLMGateway(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
        model=settings.llm_model,
        retry_attempts=settings.llm_retry_attempts,
        reasoning_max_tokens=settings.llm_reasoning_max_tokens,
    )
    testing_gateway = HTTPTestingSystemGateway(
        base_url=settings.testing_system_base_url,
        api_token=settings.testing_system_api_token,
    )

    async def _noop_dispatcher(*_: object) -> None:
        return None

    llm_job_queue: Any
    if settings.llm_queue_backend == LLMQueueBackend.CELERY:
        from competency_system.infrastructure.llm.celery_app import create_celery_app
        from competency_system.infrastructure.llm.celery_job_queue import (
            CeleryLLMJobQueue,
        )

        llm_job_queue = CeleryLLMJobQueue(
            create_celery_app(
                redis_url=settings.redis_url,
                queue_name=settings.celery_queue_name,
                result_expires_seconds=settings.celery_result_expires_seconds,
                log_level=settings.log_level,
                environment=settings.environment,
            ),
            queue_name=settings.celery_queue_name,
        )
    else:
        llm_job_queue = InMemoryLLMJobQueue(_noop_dispatcher)

    app.state.db_engine = db_engine
    app.state.session_factory = session_factory
    app.state.llm_gateway = llm_gateway
    app.state.testing_system_gateway = testing_gateway
    app.state.llm_job_queue = llm_job_queue
    app.state.rebuild_task_mapping_config = RebuildTaskMappingConfig(
        max_parallel_requests=settings.llm_max_parallel_requests,
        stage_timeout_seconds=settings.llm_stage_timeout_seconds,
        task_prompt_version=settings.llm_task_prompt_version,
    )
    app.state.auth_cookie_config = AuthCookieConfig(
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        refresh_token_expire_days=settings.refresh_token_expire_days,
        path=settings.auth_cookie_path,
    )
    app.state.testing_system_webhook_secret = settings.testing_system_webhook_secret

    await ensure_bootstrap_admin(session_factory, settings)

    logger.info(
        "application_started",
        app_name=settings.app_name,
        debug=settings.debug,
        llm_queue_backend=settings.llm_queue_backend,
    )

    try:
        yield
    finally:
        await llm_job_queue.close()
        await testing_gateway.close()
        await llm_gateway.close()
        await db_engine.dispose()
        logger.info("application_stopped", app_name=settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(log_level=settings.log_level, environment=settings.environment)
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=app_lifespan,
        root_path=settings.api_root_path,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_observability_middleware)

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(vacancies_router, prefix=settings.api_prefix)
    app.include_router(tasks_router, prefix=settings.api_prefix)
    app.include_router(admin_tasks_router, prefix=settings.api_prefix)
    app.include_router(admin_users_router, prefix=settings.api_prefix)
    app.include_router(webhook_router, prefix=settings.api_prefix)
    app.include_router(candidates_router, prefix=settings.api_prefix)
    app.include_router(ranking_router, prefix=settings.api_prefix)

    app.add_exception_handler(
        ApplicationError,
        cast(Any, application_exception_handler),
    )
    app.add_exception_handler(Exception, unexpected_exception_handler)
    return app


app = create_app()
