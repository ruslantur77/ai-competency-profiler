from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from competency_system.application.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from competency_system.infrastructure.logging import get_logger

logger = get_logger(__name__)


def application_exception_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    match exc:
        case NotFoundError():
            status_code = status.HTTP_404_NOT_FOUND
        case ConflictError():
            status_code = status.HTTP_409_CONFLICT
        case ValidationError():
            status_code = status.HTTP_400_BAD_REQUEST
        case _:
            status_code = status.HTTP_400_BAD_REQUEST

    logger.warning(
        "application_error",
        path=request.url.path,
        method=request.method,
        error_type=exc.__class__.__name__,
        detail=str(exc),
    )
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
    )


def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_error",
        path=request.url.path,
        method=request.method,
        error_type=exc.__class__.__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Unexpected error"},
    )
