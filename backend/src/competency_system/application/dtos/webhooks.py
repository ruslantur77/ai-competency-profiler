from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum, auto
from uuid import UUID

from competency_system.domain.entities.base import CreatedAtEntity, Entity


class WebhookEventStatus(StrEnum):
    """Status of webhook event processing."""

    PENDING = auto()
    PROCESSING = auto()
    PROCESSED = auto()
    FAILED = auto()


@dataclass(kw_only=True)
class WebhookEventPayload:
    data: dict[str, object] = field(default_factory=dict)


@dataclass(kw_only=True)
class RankingSnapshotPayload:
    data: dict[str, object] = field(default_factory=dict)


@dataclass(kw_only=True)
class WebhookEvent(Entity):
    event_id: str
    vacancy_id: UUID
    candidate_external_id: str
    task_external_id: str
    status: WebhookEventStatus = WebhookEventStatus.PENDING
    error_message: str | None = None
    candidate_id: UUID | None = None
    test_result_id: UUID | None = None
    payload: WebhookEventPayload = field(default_factory=WebhookEventPayload)
    processed_at: datetime | None = None

    def __post_init__(self) -> None:
        if isinstance(self.payload, dict):
            self.payload = WebhookEventPayload(data=self.payload)


@dataclass(kw_only=True)
class RankingSnapshot(CreatedAtEntity):
    id: UUID
    vacancy_id: UUID
    payload: RankingSnapshotPayload = field(default_factory=RankingSnapshotPayload)
    calculated_at: datetime

    def __post_init__(self) -> None:
        if isinstance(self.payload, dict):
            self.payload = RankingSnapshotPayload(data=self.payload)
