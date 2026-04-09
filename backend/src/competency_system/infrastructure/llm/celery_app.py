from __future__ import annotations

from celery import Celery

from competency_system.infrastructure.logging import configure_logging

celery_app = Celery("competency_system_llm_jobs")


def configure_celery_app(
    app: Celery,
    *,
    redis_url: str,
    queue_name: str,
    result_expires_seconds: int,
    log_level: str,
    environment: str,
) -> Celery:
    configure_logging(log_level=log_level, environment=environment)
    app.conf.update(
        broker_url=redis_url,
        result_backend=redis_url,
        task_default_queue=queue_name,
        task_track_started=True,
        result_expires=result_expires_seconds,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        broker_connection_retry_on_startup=True,
    )
    return app


def create_celery_app(
    *,
    redis_url: str,
    queue_name: str,
    result_expires_seconds: int,
    log_level: str,
    environment: str,
) -> Celery:
    app = Celery("competency_system_llm_jobs")
    return configure_celery_app(
        app,
        redis_url=redis_url,
        queue_name=queue_name,
        result_expires_seconds=result_expires_seconds,
        log_level=log_level,
        environment=environment,
    )
