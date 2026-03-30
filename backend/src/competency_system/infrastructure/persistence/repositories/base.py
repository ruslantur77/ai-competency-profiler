from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import Repository


class SQLAlchemyRepository[DomainT, OrmT](Repository[DomainT]):
    model: type[OrmT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def load_options(self, include: object | None = None) -> Sequence[Any]:
        return ()

    async def get(
        self,
        entity_id: UUID,
        *,
        include: object | None = None,
    ) -> DomainT | None:
        model = await self._session.get(
            self.model,
            entity_id,
            options=list(self.load_options(include)),
        )
        if model is None:
            return None
        return self.to_domain(model)

    async def list(self, *, include: object | None = None) -> Sequence[DomainT]:
        statement = select(self.model).options(*self.load_options(include))
        result = await self._session.scalars(statement)
        return [self.to_domain(model) for model in result.all()]

    async def add(self, entity: DomainT) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()

    def to_domain(self, model: OrmT) -> DomainT:
        raise NotImplementedError

    def to_model(self, entity: DomainT) -> OrmT:
        raise NotImplementedError


def normalize_include[T](include: Collection[T] | None) -> frozenset[T]:
    return frozenset(include or ())
