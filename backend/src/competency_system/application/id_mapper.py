from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol
from uuid import UUID


class CatalogItem(Protocol):
    id: UUID


class IDMapper:
    def __init__(self, items: Sequence[CatalogItem]) -> None:
        self._llm_id_to_uuid = {
            index: item.id for index, item in enumerate(items, start=1)
        }
        self._uuid_to_llm_id = {
            item.id: index for index, item in enumerate(items, start=1)
        }
        self._uuid_to_item = {item.id: item for item in items}
        self._items = items

    def to_prompt_items(
        self, dict_function: Callable[[CatalogItem], dict[str, str]]
    ) -> list[dict[str, object]]:
        return [
            {"id": index, **dict_function(item)}
            for index, item in enumerate(self._items, start=1)
        ]

    def get_item_id(self, llm_id: int) -> UUID | None:
        return self._llm_id_to_uuid.get(llm_id)

    def get_llm_id(self, uuid: UUID) -> int | None:
        return self._uuid_to_llm_id.get(uuid)

    def get_item_ids(self, llm_ids: list[int]) -> list[UUID]:
        return [
            uuid for llm_id in llm_ids if (uuid := self._llm_id_to_uuid.get(llm_id))
        ]

    def get_llm_ids(self, uuids: list[UUID]) -> list[int]:
        return [llm_id for uuid in uuids if (llm_id := self._uuid_to_llm_id.get(uuid))]
