from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict
from sqlalchemy import inspect


class BaseDTO(BaseModel):
    """Базовый DTO с кастомным model_validate для SQLAlchemy ORM.

    Позволяет сериализовать ORM объекты без lazy loading.
    """

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> Self:
        """Валидирует SQLAlchemy ORM объект или обычный dict."""
        if not hasattr(obj, "__mapper__"):
            return super().model_validate(obj, **kwargs)

        # Serialize SQLAlchemy ORM object avoiding lazy loading
        def serialize(o: Any) -> Any:
            insp = inspect(o)
            data = {}
            for name in insp.attrs.keys():
                if name in insp.unloaded:
                    continue
                val = getattr(o, name)
                if hasattr(val, "__mapper__"):
                    data[name] = serialize(val)
                elif isinstance(val, list):
                    data[name] = [
                        serialize(item) if hasattr(item, "__mapper__") else item
                        for item in val
                    ]
                else:
                    data[name] = val
            return data

        return super().model_validate(serialize(obj), **kwargs)
