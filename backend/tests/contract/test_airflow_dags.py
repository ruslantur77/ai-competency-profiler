from __future__ import annotations

from importlib import import_module

import pytest

pytest.importorskip("airflow")
airflow_docker = pytest.importorskip("airflow.providers.docker.operators.docker")
DockerOperator = airflow_docker.DockerOperator

task_sync = import_module(
    "competency_system.presentation.airflow.dags.task_sync"
).task_sync

pytestmark = [pytest.mark.contract, pytest.mark.optional_dep]


def test_airflow_dag_ids() -> None:
    assert task_sync.dag_id == "task_sync"


def test_airflow_dag_task_counts() -> None:
    assert len(task_sync.tasks) == 1


def test_task_sync_uses_docker_operator() -> None:
    operator = task_sync.get_task("sync_tasks")
    assert isinstance(operator, DockerOperator)


def test_task_sync_hourly_schedule() -> None:
    schedule = getattr(task_sync, "schedule", None)
    if schedule is None:
        schedule = getattr(task_sync, "schedule_interval", None)
    assert str(schedule) == "@hourly"
