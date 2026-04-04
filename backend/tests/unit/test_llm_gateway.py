from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from competency_system.application.ports.llm import LLMMessage
from competency_system.infrastructure.llm.errors import LLMAdapterError
from competency_system.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMGateway,
)
from competency_system.infrastructure.settings import Settings

pytestmark = pytest.mark.unit

llm_module = import_module("competency_system.infrastructure.llm.openai_compatible")


class EchoResponseDTO(BaseModel):
    answer: str


class _FakeCompletions:
    def __init__(self, response_content: str, failures_before_success: int = 0) -> None:
        self._response_content = response_content
        self._failures_before_success = failures_before_success
        self.calls = 0

    async def create(self, **_: object) -> SimpleNamespace:
        self.calls += 1
        if self._failures_before_success > 0:
            self._failures_before_success -= 1
            raise RuntimeError("temporary failure")
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._response_content),
                )
            ]
        )


class _FakeClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


async def test_llm_gateway_retries_and_parses_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completions = _FakeCompletions('{"answer": "ok"}', failures_before_success=1)
    fake_client = _FakeClient(completions)
    monkeypatch.setattr(llm_module, "AsyncOpenAI", lambda **_: fake_client)

    gateway = OpenAICompatibleLLMGateway(
        Settings(
            llm_retry_attempts=2,
            llm_timeout_seconds=1.0,
        )
    )
    result = await gateway.generate(
        [LLMMessage(role="user", content="hello")],
        EchoResponseDTO,
    )

    assert result.answer == "ok"
    assert completions.calls == 2


async def test_llm_gateway_wraps_invalid_json_after_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completions = _FakeCompletions("not json")
    fake_client = _FakeClient(completions)
    monkeypatch.setattr(llm_module, "AsyncOpenAI", lambda **_: fake_client)

    gateway = OpenAICompatibleLLMGateway(
        Settings(
            llm_retry_attempts=2,
            llm_timeout_seconds=1.0,
        )
    )

    with pytest.raises(LLMAdapterError):
        await gateway.generate(
            [LLMMessage(role="user", content="hello")],
            EchoResponseDTO,
        )

    assert completions.calls == 2
