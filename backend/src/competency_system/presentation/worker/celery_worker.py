from __future__ import annotations

from competency_system.infrastructure.llm import (
    celery_tasks as _celery_tasks,  # noqa: F401
)
from competency_system.infrastructure.llm.celery_app import (
    celery_app,
    configure_celery_app,
)
from competency_system.infrastructure.settings import get_settings

settings = get_settings()
configure_celery_app(
    celery_app,
    redis_url=settings.redis_url,
    queue_name=settings.celery_queue_name,
    result_expires_seconds=settings.celery_result_expires_seconds,
    log_level=settings.log_level,
    environment=settings.environment,
)

__all__ = ["celery_app"]
