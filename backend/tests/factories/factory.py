from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable


class AbstractFactory[FieldsT, SchemaT, OrmT](ABC):
    def __init__(
        self,
        insert_async_func: Callable[[OrmT], Awaitable[OrmT]] | None = None,
    ) -> None:
        self.insert_async_func = insert_async_func

    @abstractmethod
    def make(self, fields: FieldsT | None = None) -> SchemaT:
        raise NotImplementedError

    @abstractmethod
    def make_orm(self, fields: FieldsT | None = None) -> OrmT:
        raise NotImplementedError

    async def insert_to_database(
        self,
        fields: FieldsT | None = None,
        insert_async_func: Callable[[OrmT], Awaitable[OrmT]] | None = None,
    ) -> OrmT:
        orm = self.make_orm(fields)
        insert = insert_async_func or self.insert_async_func
        if insert is None:
            raise ValueError("No insert async function passed")
        return await insert(orm)
