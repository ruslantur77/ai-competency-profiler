from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from competency_system.domain.entities.base import Entity


@dataclass(kw_only=True)
class WebhookEvent(Entity):
    event_id: str
    vacancy_id: UUID
    candidate_external_id: str
    task_external_id: str
    status: str = "processing"
    error_message: str | None = None
    candidate_id: UUID | None = None
    test_result_id: UUID | None = None
    payload: dict[str, object] | None = None
    processed_at: datetime | None = None


@dataclass(kw_only=True)
class RankingSnapshot(Entity):
    vacancy_id: UUID
    payload: dict[str, object]
    calculated_at: datetime
