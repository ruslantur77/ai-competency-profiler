from __future__ import annotations

import asyncio
import logging

import pytest
from pydantic import BaseModel

from competency_system.application.llm.llm_orchestrator import (
    LLMCallSpec,
    StructuredLLMOrchestrator,
    normalize_weighted_items,
)
from competency_system.application.ports.llm import LLMMessage

pytestmark = pytest.mark.unit


class _Response(BaseModel):
    value: int


class _Item(BaseModel):
    weight: float


class _FlakyLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, messages, response_model, *, temperature=0.2):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary")
        return response_model.model_validate({"value": 7})


class _SlowLLM:
    async def generate(self, messages, response_model, *, temperature=0.2):  # type: ignore[no-untyped-def]
        await asyncio.sleep(0.05)
        return response_model.model_validate({"value": 1})


class _FastLLM:
    async def generate(self, messages, response_model, *, temperature=0.2):  # type: ignore[no-untyped-def]
        payload = int(messages[0].content)
        return response_model.model_validate({"value": payload})


async def test_structured_llm_orchestrator_retries_and_returns_result(
    caplog: pytest.LogCaptureFixture,
) -> None:
    llm = _FlakyLLM()
    orchestrator = StructuredLLMOrchestrator(
        llm,
        max_parallel_requests=1,
        stage_timeout_seconds=2.0,
        stage_retry_attempts=2,
    )

    with caplog.at_level(logging.INFO):
        result = await orchestrator.run(
            LLMCallSpec(
                stage="s1",
                messages=[LLMMessage(role="user", content="x")],
                response_model=_Response,
            )
        )

    assert result.value == 7
    assert llm.calls == 2
    assert "llm_stage_started" in caplog.text
    assert "llm_stage_attempt_failed" in caplog.text
    assert "llm_stage_finished" in caplog.text


async def test_structured_llm_orchestrator_times_out(
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestrator = StructuredLLMOrchestrator(
        _SlowLLM(),
        max_parallel_requests=1,
        stage_timeout_seconds=0.01,
        stage_retry_attempts=1,
    )

    with caplog.at_level(logging.INFO), pytest.raises(TimeoutError):
        await orchestrator.run(
            LLMCallSpec(
                stage="timeout",
                messages=[LLMMessage(role="user", content="x")],
                response_model=_Response,
            )
        )
    assert "llm_stage_failed" in caplog.text


async def test_structured_llm_orchestrator_run_many_handles_empty_specs() -> None:
    orchestrator = StructuredLLMOrchestrator(
        _FlakyLLM(), max_parallel_requests=2, stage_timeout_seconds=1.0
    )

    result = await orchestrator.run_many([])

    assert result == []


async def test_structured_llm_orchestrator_run_many_preserves_result_order() -> None:
    orchestrator = StructuredLLMOrchestrator(
        _FastLLM(), max_parallel_requests=2, stage_timeout_seconds=1.0
    )
    specs = [
        LLMCallSpec(
            stage="s1",
            messages=[LLMMessage(role="user", content="1")],
            response_model=_Response,
        ),
        LLMCallSpec(
            stage="s2",
            messages=[LLMMessage(role="user", content="2")],
            response_model=_Response,
        ),
    ]

    result = await orchestrator.run_many(specs)

    assert [item.value for item in result] == [1, 2]


def test_normalize_weighted_items_assigns_equal_weights_when_total_zero() -> None:
    items = [_Item(weight=0.0), _Item(weight=-2.0)]

    normalized = normalize_weighted_items(items)

    assert normalized[0].weight == pytest.approx(0.5)
    assert normalized[1].weight == pytest.approx(0.5)


def test_normalize_weighted_items_normalizes_positive_weights() -> None:
    items = [_Item(weight=2.0), _Item(weight=1.0)]

    normalized = normalize_weighted_items(items)

    assert normalized[0].weight == pytest.approx(2 / 3)
    assert normalized[1].weight == pytest.approx(1 / 3)
