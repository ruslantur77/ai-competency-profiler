from enum import StrEnum, auto


class WebhookEventStatus(StrEnum):
    """Status of webhook event processing."""

    PROCESSING = auto()
    PROCESSED = auto()
    FAILED = auto()
