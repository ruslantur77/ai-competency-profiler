from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xfail(strict=False)
def test_task_sync_dag_contains_precheck_and_sync_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("airflow")
    pytest.importorskip("airflow.providers.docker.operators.docker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/app")

    from competency_system.presentation.airflow.dags.task_sync import task_sync

    assert task_sync is not None
    assert {"precheck_runtime", "sync_tasks"}.issubset(task_sync.task_ids)

    precheck_runtime = task_sync.get_task("precheck_runtime")
    sync_tasks = task_sync.get_task("sync_tasks")

    assert sync_tasks.upstream_task_ids == {"precheck_runtime"}
    assert precheck_runtime.downstream_task_ids == {"sync_tasks"}
