from __future__ import annotations

import json
import re
from json import JSONDecodeError
from typing import Any

from openai import AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from competency_system.application.ports.llm import LLMGateway, LLMMessage, LLMResponseT
from competency_system.infrastructure.llm.errors import LLMAdapterError
from competency_system.infrastructure.logging import get_logger
from competency_system.infrastructure.settings import Settings, get_settings


class OpenAICompatibleLLMGateway(LLMGateway):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._logger = get_logger(__name__).bind(component="llm", provider="openai")
        self._client = AsyncOpenAI(
            api_key=self._settings.llm_api_key or None,
            base_url=self._settings.llm_base_url,
            timeout=self._settings.llm_timeout_seconds,
            max_retries=0,
        )

    async def close(self) -> None:
        await self._client.close()

    async def generate(
        self,
        messages: list[LLMMessage],
        response_model: type[LLMResponseT],
        *,
        temperature: float = 0.2,
    ) -> LLMResponseT:
        attempts = max(1, self._settings.llm_retry_attempts)
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(attempts),
                wait=wait_exponential_jitter(initial=1.0, max=8.0),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    return await self._generate_once(
                        messages,
                        response_model,
                        temperature=temperature,
                    )
        except Exception as exc:  # pragma: no cover - infra boundary
            self._logger.exception(
                "llm_request_failed",
                model=self._settings.llm_model,
                attempts=attempts,
            )
            raise LLMAdapterError(
                f"LLM request failed for model {self._settings.llm_model}"
            ) from exc

    async def _generate_once(
        self,
        messages: list[LLMMessage],
        response_model: type[LLMResponseT],
        *,
        temperature: float,
    ) -> LLMResponseT:
        self._logger.info(
            "llm_request_started",
            model=self._settings.llm_model,
            message_count=len(messages),
            temperature=temperature,
        )
        response = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            messages=[
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
            extra_body=self._extra_body(),
        )
        content = response.choices[0].message.content or "{}"
        payload = self._extract_json(content)
        result = response_model.model_validate(payload)
        self._logger.info(
            "llm_request_finished",
            model=self._settings.llm_model,
            message_count=len(messages),
        )
        return result

    def _extract_json(self, content: str) -> Any:
        cleaned = re.sub(r"```json|```", "", content, flags=re.IGNORECASE).strip()
        try:
            return json.loads(cleaned)
        except JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match is None:
                raise ValueError("LLM response does not contain a JSON object") from None
            return json.loads(match.group())

    def _extra_body(self) -> dict[str, object] | None:
        if self._settings.llm_reasoning_max_tokens <= 0:
            return None
        return {"reasoning": {"max_tokens": self._settings.llm_reasoning_max_tokens}}
