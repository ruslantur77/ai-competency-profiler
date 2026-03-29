from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:  # Airflow 2.x
    from airflow.operators.python import get_current_context  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - import fallback
    try:
        from airflow.decorators import get_current_context  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - import fallback
        from airflow.sdk import get_current_context  # type: ignore[attr-defined]


def get_dag_conf() -> dict[str, Any]:
    context = get_current_context()
    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", None)
    if conf is None:
        return {}
    if isinstance(conf, Mapping):
        return dict(conf)
    return dict(conf)
