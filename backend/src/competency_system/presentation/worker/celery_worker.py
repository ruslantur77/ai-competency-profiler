from __future__ import annotations

from competency_system.infrastructure.llm import (
    celery_tasks as _celery_tasks,  # noqa: F401
)
from competency_system.infrastructure.llm.celery_app import get_celery_app

celery_app = get_celery_app()

__all__ = ["celery_app"]
