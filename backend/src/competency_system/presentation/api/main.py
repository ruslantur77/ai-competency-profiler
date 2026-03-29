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
from competency_system.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMGateway,
)
from competency_system.infrastructure.logging import configure_logging, get_logger
from competency_system.infrastructure.settings import get_settings
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

API_PREFIX = "/api/v1"
logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)

    db_engine, session_factory = create_engine_and_session_factory(settings)
    llm_gateway = OpenAICompatibleLLMGateway(settings)
    testing_gateway = HTTPTestingSystemGateway(settings)

    app.state.db_engine = db_engine
    app.state.session_factory = session_factory
    app.state.llm_gateway = llm_gateway
    app.state.testing_system_gateway = testing_gateway

    await ensure_bootstrap_admin(session_factory, settings)

    logger.info("application_started", app_name=settings.app_name, debug=settings.debug)

    try:
        yield
    finally:
        await testing_gateway.close()
        await llm_gateway.close()
        await db_engine.dispose()
        logger.info("application_stopped", app_name=settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=app_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_observability_middleware)

    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(vacancies_router, prefix=API_PREFIX)
    app.include_router(tasks_router, prefix=API_PREFIX)
    app.include_router(admin_tasks_router, prefix=API_PREFIX)
    app.include_router(webhook_router, prefix=API_PREFIX)
    app.include_router(candidates_router, prefix=API_PREFIX)
    app.include_router(ranking_router, prefix=API_PREFIX)

    app.add_exception_handler(
        ApplicationError,
        cast(Any, application_exception_handler),
    )
    app.add_exception_handler(Exception, unexpected_exception_handler)
    return app


app = create_app()
