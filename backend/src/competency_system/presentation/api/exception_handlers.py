from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from competency_system.application.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
    map_value_error,
)
from competency_system.infrastructure.logging import get_logger

logger = get_logger(__name__)


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else ""


def _error_envelope(
    *,
    request: Request,
    code: str,
    message: str,
    details: Any | None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": jsonable_encoder(details),
        "request_id": _request_id(request),
    }


def application_exception_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    match exc:
        case NotFoundError():
            status_code = status.HTTP_404_NOT_FOUND
        case ConflictError():
            status_code = status.HTTP_409_CONFLICT
        case ServiceUnavailableError():
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
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
        content=_error_envelope(
            request=request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
    )


def value_error_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    mapped = map_value_error(exc)
    return application_exception_handler(request, mapped)


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    details = exc.detail
    message = details
    code_map = {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_401_UNAUTHORIZED: "unauthorized",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_409_CONFLICT: "conflict",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "validation_error",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_envelope(
            request=request,
            code=code_map.get(exc.status_code, "http_error"),
            message=message,
            details=details,
        ),
        headers=exc.headers,
    )


def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_envelope(
            request=request,
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        ),
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
        content=_error_envelope(
            request=request,
            code="internal_error",
            message="Unexpected error",
            details=None,
        ),
    )
