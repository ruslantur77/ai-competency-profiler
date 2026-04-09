from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class AuthCookieConfig:
    secure: bool
    samesite: Literal["lax", "strict", "none"] | None
    refresh_token_expire_days: int


@dataclass(frozen=True, slots=True)
class RebuildTaskMappingConfig:
    max_parallel_requests: int
    stage_timeout_seconds: float
    task_prompt_version: str
