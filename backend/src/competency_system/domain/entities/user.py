from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from competency_system.domain.entities.base import CreatedAtEntity, Entity
from competency_system.domain.value_objects import UserRole


@dataclass(kw_only=True)
class User(Entity):
    email: str
    role: UserRole = UserRole.HR
    is_active: bool = True
    hashed_password: str


@dataclass(kw_only=True)
class RefreshToken(CreatedAtEntity):
    jti: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None

    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)
