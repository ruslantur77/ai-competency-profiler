from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthCookieConfig:
    secure: bool
    samesite: str
    refresh_token_expire_days: int


@dataclass(frozen=True, slots=True)
class RebuildTaskMappingConfig:
    max_parallel_requests: int
    stage_timeout_seconds: float
    task_prompt_version: str
