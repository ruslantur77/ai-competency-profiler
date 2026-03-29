from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from competency_system.infrastructure.logging import get_logger

REQUEST_ID_HEADER = "X-Request-ID"


async def request_observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
    started_at = time.perf_counter()
    logger = get_logger(__name__).bind(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    request.state.request_id = request_id
    bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    logger.info("request_started")
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
        logger.exception("request_failed", duration_ms=duration_ms)
        clear_contextvars()
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "request_finished",
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    clear_contextvars()
    return response
