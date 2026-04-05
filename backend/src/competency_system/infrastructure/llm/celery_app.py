from __future__ import annotations

from functools import lru_cache

from celery import Celery

from competency_system.infrastructure.logging import configure_logging
from competency_system.infrastructure.settings import Settings, get_settings


def create_celery_app(settings: Settings) -> Celery:
    configure_logging(settings)
    app = Celery(
        "competency_system_llm_jobs",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )
    app.conf.update(
        task_default_queue=settings.celery_queue_name,
        task_track_started=True,
        result_expires=settings.celery_result_expires_seconds,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        broker_connection_retry_on_startup=True,
    )
    return app


@lru_cache(maxsize=1)
def get_celery_app() -> Celery:
    return create_celery_app(get_settings())
