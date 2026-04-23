from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    default_code = "application_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details


class NotFoundError(ApplicationError):
    default_code = "not_found"


class ConflictError(ApplicationError):
    default_code = "conflict"


class ValidationError(ApplicationError):
    default_code = "validation_error"


class ServiceUnavailableError(ApplicationError):
    default_code = "service_unavailable"


def map_value_error(exc: ValueError) -> ApplicationError:
    message = str(exc)
    lowered = message.lower()
    if "not found" in lowered:
        return NotFoundError(message)
    if (
        "already exists" in lowered
        or "already assigned" in lowered
        or "already handled" in lowered
        or "is processing" in lowered
        or "conflict" in lowered
    ):
        return ConflictError(message)
    return ValidationError(message)
