from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

import structlog

from competency_system.infrastructure.settings import Settings, get_settings

_LOGGING_CONFIGURED = False
Processor = Callable[
    [Any, str, MutableMapping[str, Any]],
    Mapping[str, Any] | str | bytes | bytearray | tuple[Any, ...],
]


def configure_logging(settings: Settings | None = None) -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    resolved_settings = settings or get_settings()
    log_level = getattr(logging, resolved_settings.log_level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=shared_processors,
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    json_handler = logging.StreamHandler()
    json_handler.setFormatter(json_formatter)

    handlers = [console_handler]

    if resolved_settings.environment == "production":
        handlers = [json_handler]
    elif resolved_settings.environment == "local":
        handlers = [console_handler]
    else:
        handlers = [console_handler, json_handler]

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        framework_logger = logging.getLogger(logger_name)
        framework_logger.handlers = root_logger.handlers
        framework_logger.setLevel(log_level)
        framework_logger.propagate = False

    _LOGGING_CONFIGURED = True


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)
