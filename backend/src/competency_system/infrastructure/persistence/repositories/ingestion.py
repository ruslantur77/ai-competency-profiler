from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from competency_system.domain.entities import RankingSnapshot, WebhookEvent
from competency_system.infrastructure.persistence.mappers import (
    ranking_snapshot_from_orm,
    ranking_snapshot_to_orm,
    webhook_event_from_orm,
    webhook_event_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    RankingSnapshotOrm,
    WebhookEventOrm,
)
from competency_system.infrastructure.persistence.repositories.base import SQLAlchemyRepository


class WebhookEventRepository(SQLAlchemyRepository[WebhookEvent, WebhookEventOrm]):
    model = WebhookEventOrm

    async def get_by_event_id(
        self,
        event_id: str,
        *,
        include: object | None = None,
    ) -> WebhookEvent | None:
        statement = select(WebhookEventOrm).where(WebhookEventOrm.event_id == event_id)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: WebhookEventOrm) -> WebhookEvent:
        return webhook_event_from_orm(model)

    def to_model(self, entity: WebhookEvent) -> WebhookEventOrm:
        return webhook_event_to_orm(entity)


class RankingSnapshotRepository(
    SQLAlchemyRepository[RankingSnapshot, RankingSnapshotOrm]
):
    model = RankingSnapshotOrm

    async def get_by_vacancy(
        self,
        vacancy_id: UUID,
        *,
        include: object | None = None,
    ) -> RankingSnapshot | None:
        statement = select(RankingSnapshotOrm).where(
            RankingSnapshotOrm.vacancy_id == vacancy_id
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: RankingSnapshotOrm) -> RankingSnapshot:
        return ranking_snapshot_from_orm(model)

    def to_model(self, entity: RankingSnapshot) -> RankingSnapshotOrm:
        return ranking_snapshot_to_orm(entity)
