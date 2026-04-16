from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

ItemT = TypeVar("ItemT")


class PaginatedItemsDTO[ItemT](BaseModel):
    items: list[ItemT]
    total: int
    limit: int
    offset: int
