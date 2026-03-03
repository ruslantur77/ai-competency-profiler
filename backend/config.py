from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Any, get_type_hints

from dotenv import load_dotenv


def _convert(value: str, to_type: type) -> Any:
    if to_type is bool:
        return value.lower() in {"1", "true", "yes"}
    return to_type(value)


@dataclass(frozen=True)
class Config:
    api_key: str = field(metadata={"env": "API_KEY"})
    base_url: str = field(metadata={"env": "BASE_URL"})
    model: str = field(metadata={"env": "MODEL"})

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()

        type_hints = get_type_hints(cls)
        kwargs = {}

        for f in fields(cls):
            env_name = f.name.upper()
            value = os.getenv(env_name)

            if value is None:
                raise ValueError(f"{env_name} is not set")

            real_type = type_hints[f.name]
            kwargs[f.name] = _convert(value, real_type)

        return cls(**kwargs)


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
