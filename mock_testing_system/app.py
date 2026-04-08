from __future__ import annotations

import hashlib
import os
import random
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

GENERATOR_VERSION = "v1"
DEFAULT_SEED = "mock-testing-system"


class ExternalTask(BaseModel):
    external_id: str
    title: str
    description: str
    type: str = Field(pattern="^(code|test)$")
    tags: list[str]
    created_at: datetime


TASK_BLUEPRINTS: list[dict[str, object]] = [
    {
        "title": "Build paginated REST endpoint",
        "description": (
            "Implement endpoint with pagination, filtering and sorting. "
            "Validate query params and return stable output schema."
        ),
        "tags": ["python", "fastapi", "rest", "pagination"],
        "type": "code",
    },
    {
        "title": "Optimize SQL query plan",
        "description": (
            "Refactor query for lower latency on large dataset. "
            "Explain selected indexes and expected complexity."
        ),
        "tags": ["sql", "postgres", "performance", "indexing"],
        "type": "code",
    },
    {
        "title": "Implement async retry worker",
        "description": (
            "Process queue messages with retries, backoff and idempotency key checks. "
            "Handle transient failures without duplicate side effects."
        ),
        "tags": ["python", "asyncio", "queues", "reliability"],
        "type": "code",
    },
    {
        "title": "Write API integration tests",
        "description": (
            "Cover happy path and edge cases for an API endpoint. "
            "Use deterministic fixtures and clear assertions."
        ),
        "tags": ["pytest", "testing", "api", "integration"],
        "type": "test",
    },
    {
        "title": "Design cache invalidation strategy",
        "description": (
            "Propose cache key model and invalidation logic for frequently updated entities. "
            "Describe consistency tradeoffs."
        ),
        "tags": ["redis", "caching", "backend", "architecture"],
        "type": "code",
    },
    {
        "title": "Harden webhook handler",
        "description": (
            "Verify signature, protect from replay and persist idempotency markers. "
            "Return appropriate statuses for retries."
        ),
        "tags": ["webhook", "security", "backend", "idempotency"],
        "type": "code",
    },
]

app = FastAPI(title="mock-testing-system", version="1.0.0")


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _ensure_utc(name: str, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{name}' must include timezone",
        )
    if value.utcoffset() != timedelta(0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{name}' must be UTC (Z)",
        )
    return value.astimezone(UTC)


def _check_auth(authorization: str | None) -> None:
    expected_token = os.getenv("TESTING_SYSTEM_API_TOKEN", "").strip()
    if not expected_token:
        return

    expected_value = f"Bearer {expected_token}"
    if authorization != expected_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )


def _build_seed(start: datetime, end: datetime) -> tuple[str, int]:
    configured_seed = os.getenv("MOCK_TESTING_SYSTEM_SEED", DEFAULT_SEED)
    key = f"{_utc_iso(start)}|{_utc_iso(end)}|{configured_seed}|{GENERATOR_VERSION}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return key, int.from_bytes(digest[:8], byteorder="big", signed=False)


def _sample_count(rng: random.Random, start: datetime, end: datetime) -> int:
    duration_days = (end - start).total_seconds() / 86_400
    baseline = max(1, round(duration_days * 12))
    jitter = rng.randint(-4, 4)
    return max(1, min(500, baseline + jitter))


def _external_id(seed_key: str, index: int) -> str:
    value = hashlib.sha256(f"{seed_key}|{index}".encode("utf-8")).hexdigest()[:12]
    return f"mock-task-{value}"


def _generate_tasks(start: datetime, end: datetime) -> list[ExternalTask]:
    seed_key, seed_value = _build_seed(start, end)
    rng = random.Random(seed_value)
    count = _sample_count(rng, start, end)
    window_seconds = (end - start).total_seconds()

    tasks: list[ExternalTask] = []
    for index in range(count):
        blueprint = TASK_BLUEPRINTS[rng.randrange(len(TASK_BLUEPRINTS))]
        offset = rng.random() * window_seconds
        created_at = start + timedelta(seconds=offset)

        tags = list(blueprint["tags"])
        rng.shuffle(tags)
        selected_tags = sorted(tags[: rng.randint(2, min(4, len(tags)))])

        tasks.append(
            ExternalTask(
                external_id=_external_id(seed_key, index),
                title=str(blueprint["title"]),
                description=str(blueprint["description"]),
                type=str(blueprint["type"]),
                tags=selected_tags,
                created_at=created_at,
            )
        )

    tasks.sort(key=lambda item: (item.created_at, item.external_id))
    return tasks


@app.get("/external/tasks", response_model=list[ExternalTask])
async def list_external_tasks(
    start: Annotated[datetime, Query(...)],
    end: Annotated[datetime, Query(...)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> list[ExternalTask]:
    _check_auth(authorization)
    start_utc = _ensure_utc("start", start)
    end_utc = _ensure_utc("end", end)

    if end_utc <= start_utc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'end' must be greater than 'start'",
        )

    return _generate_tasks(start_utc, end_utc)
