from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

LLMResponseT = TypeVar("LLMResponseT", bound=BaseModel)


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class LLMGateway(Protocol):
    async def generate(
        self,
        messages: list[LLMMessage],
        response_model: type[LLMResponseT],
        *,
        temperature: float = 0.2,
    ) -> LLMResponseT: ...
