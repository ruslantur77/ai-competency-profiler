from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class Entity:
    """Base class for entities with UUID PK and audit timestamps."""

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(kw_only=True)
class CreatedAtEntity:
    """Base class for entities that only track creation time."""

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
