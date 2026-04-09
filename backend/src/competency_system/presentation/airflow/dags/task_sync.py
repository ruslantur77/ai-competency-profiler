from __future__ import annotations

import os
from datetime import UTC, datetime

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import dag

DEFAULT_ARGS = {
    "owner": "competency-system",
    "retries": 1,
}

TASK_SYNC_IMAGE = os.getenv("TASK_SYNC_IMAGE", "competency-system/api:latest")
AIRFLOW_DOCKER_NETWORK = os.getenv("AIRFLOW_DOCKER_NETWORK", "bridge")
START_TEMPLATE = (
    "{{ dag_run.conf.get('start') "
    "if dag_run and dag_run.conf and dag_run.conf.get('start') "
    "else data_interval_start.in_timezone('UTC').isoformat() }}"
)
END_TEMPLATE = (
    "{{ dag_run.conf.get('end') "
    "if dag_run and dag_run.conf and dag_run.conf.get('end') "
    "else (data_interval_start + macros.timedelta(hours=1)).in_timezone('UTC').isoformat() }}"  # noqa: E501
)


@dag(
    dag_id="task_sync",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    schedule="@hourly",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["tasks", "sync", "batch"],
)
def task_sync_dag() -> None:
    DockerOperator(
        task_id="sync_tasks",
        image=TASK_SYNC_IMAGE,
        docker_url="unix://var/run/docker.sock",
        network_mode=AIRFLOW_DOCKER_NETWORK,
        mount_tmp_dir=False,
        auto_remove="success",
        command=(
            "python -m competency_system.presentation.airflow.jobs.task_sync_runner "
            f'--start "{START_TEMPLATE}" '
            f'--end "{END_TEMPLATE}"'
        ),
    )


task_sync = task_sync_dag()
