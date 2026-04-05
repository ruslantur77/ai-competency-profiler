from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from competency_system.application.ports.llm import LLMGateway, LLMMessage, LLMResponseT

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMCallSpec[ResponseT: BaseModel]:
    stage: str
    messages: list[LLMMessage]
    response_model: type[ResponseT]
    temperature: float = 0.2


class StructuredLLMOrchestrator:
    """Utility wrapper for structured, retriable and throttled LLM calls."""

    def __init__(
        self,
        llm: LLMGateway,
        *,
        max_parallel_requests: int,
        stage_timeout_seconds: float,
        stage_retry_attempts: int = 2,
    ) -> None:
        self._llm = llm
        self._stage_timeout_seconds = stage_timeout_seconds
        self._stage_retry_attempts = max(1, stage_retry_attempts)
        self._semaphore = asyncio.Semaphore(max(1, max_parallel_requests))

    async def run[ResponseT: BaseModel](
        self, spec: LLMCallSpec[ResponseT]
    ) -> ResponseT:
        started = perf_counter()
        attempts_made = 0
        logger.info(
            "llm_stage_started",
            extra={
                "stage": spec.stage,
                "timeout_seconds": self._stage_timeout_seconds,
                "attempt_limit": self._stage_retry_attempts,
            },
        )
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._stage_retry_attempts),
                wait=wait_exponential_jitter(initial=0.5, max=4.0),
                retry=retry_if_exception_type(Exception),
                before_sleep=lambda state: self._log_attempt_failure(spec, state),
                reraise=True,
            ):
                with attempt:
                    attempts_made = attempt.retry_state.attempt_number
                    async with self._semaphore:
                        result = await asyncio.wait_for(
                            self._llm.generate(
                                spec.messages,
                                spec.response_model,
                                temperature=spec.temperature,
                            ),
                            timeout=self._stage_timeout_seconds,
                        )
                        duration_ms = round((perf_counter() - started) * 1000.0, 2)
                        result_view = _summarize_stage_output(result)
                        logger.info(
                            "llm_stage_finished",
                            extra={
                                "stage": spec.stage,
                                "status": "success",
                                "attempt": attempts_made,
                                "duration_ms": duration_ms,
                                "result_summary": result_view["summary"],
                                "result_sample": result_view["sample"],
                            },
                        )
                        return result
            raise RuntimeError("Retrying loop completed without returning a result")
        except Exception as exc:
            duration_ms = round((perf_counter() - started) * 1000.0, 2)
            logger.exception(
                "llm_stage_failed",
                extra={
                    "stage": spec.stage,
                    "status": "failed",
                    "attempts_made": max(attempts_made, 1),
                    "attempt_limit": self._stage_retry_attempts,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "request_messages": _serialize_messages(spec.messages),
                    "response_snapshot": None,
                },
            )
            raise

    async def run_many(
        self,
        specs: list[LLMCallSpec[LLMResponseT]],
    ) -> list[LLMResponseT]:
        if not specs:
            return []
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self.run(spec)) for spec in specs]
        return [task.result() for task in tasks]

    def _log_attempt_failure(
        self,
        spec: LLMCallSpec[BaseModel],
        state: RetryCallState,
    ) -> None:
        exc = state.outcome.exception() if state.outcome else None
        logger.warning(
            "llm_stage_attempt_failed",
            extra={
                "stage": spec.stage,
                "attempt": state.attempt_number,
                "attempt_limit": self._stage_retry_attempts,
                "error_type": type(exc).__name__ if exc else None,
                "error": str(exc) if exc else None,
            },
        )


def _serialize_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def _summarize_stage_output(
    result: BaseModel, *, sample_limit: int = 3
) -> dict[str, Any]:
    payload = result.model_dump(mode="json")
    summary: dict[str, Any] = {}
    sample: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, list):
            summary[f"{key}_count"] = len(value)
            sample[key] = value[:sample_limit]
        elif isinstance(value, dict):
            summary[f"{key}_keys"] = sorted(value.keys())
        else:
            summary[key] = value
    return {"summary": summary, "sample": sample}


def normalize_weighted_items[T: BaseModel](
    items: list[T],
    *,
    weight_attr: str = "weight",
) -> list[T]:
    if not items:
        return items
    weights = [max(0.0, float(getattr(item, weight_attr, 0.0))) for item in items]
    total = sum(weights)
    if total <= 0.0:
        equal = 1.0 / len(items)
        for item in items:
            setattr(item, weight_attr, equal)
        return items
    for item, weight in zip(items, weights, strict=False):
        setattr(item, weight_attr, weight / total)
    return items
