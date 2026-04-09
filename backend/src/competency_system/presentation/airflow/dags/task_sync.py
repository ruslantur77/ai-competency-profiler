from __future__ import annotations

import os
from datetime import UTC, datetime

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import dag
from airflow.sdk.bases.hook import BaseHook
from airflow.sdk.definitions.connection import Connection

DEFAULT_APP_DB_CONN_ID = "competency_app_db"
APP_DB_CONN_ID_ENV = "APP_DB_CONN_ID"

DEFAULT_ARGS = {
    "owner": "competency-system",
    "retries": 1,
}

TASK_SYNC_IMAGE = os.getenv("TASK_SYNC_IMAGE", "competency-system/api:latest")
AIRFLOW_DOCKER_NETWORK = os.getenv("AIRFLOW_DOCKER_NETWORK", "bridge")

RUNTIME_ENV_WHITELIST = (
    "LOG_LEVEL",
    "DEBUG",
    "ENVIRONMENT",
    "TESTING_SYSTEM_BASE_URL",
    "TESTING_SYSTEM_API_TOKEN",
    "LLM_QUEUE_BACKEND",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
    "CELERY_QUEUE_NAME",
    "CELERY_RESULT_EXPIRES_SECONDS",
)

DB_ENV_KEYS = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASS", "DB_NAME")


START_TEMPLATE = """
{{ dag_run.conf.get('start')
   if dag_run and dag_run.conf and dag_run.conf.get('start')
   else data_interval_start.in_timezone('UTC').isoformat() }}
""".strip()

END_TEMPLATE = """
{{ dag_run.conf.get('end')
   if dag_run and dag_run.conf and dag_run.conf.get('end')
   else (data_interval_start + macros.timedelta(hours=1)).in_timezone('UTC').isoformat() }}
""".strip()  # noqa: E501


def _get_airflow_connection(conn_id: str) -> Connection | None:
    """Safely get Airflow connection if Airflow is available."""
    try:
        return BaseHook.get_connection(conn_id)
    except Exception:
        return None


def _resolve_database_env() -> dict[str, str]:
    """Resolve DB configuration in priority order.

    1. Airflow connection (as DATABASE_URL)
    2. DATABASE_URL env var
    3. Individual DB_* env vars
    """
    conn_id = os.getenv(APP_DB_CONN_ID_ENV, DEFAULT_APP_DB_CONN_ID)
    connection = _get_airflow_connection(conn_id)

    if connection and hasattr(connection, "get_uri"):
        uri = connection.get_uri()
        if uri:
            return {"DATABASE_URL": str(uri)}

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"DATABASE_URL": database_url}

    db = {key: os.environ[key] for key in DB_ENV_KEYS if os.getenv(key)}
    return {
        "DATABASE_URL": f"postgresql://{db['DB_USER']}:{db['DB_PASS']}@{db['DB_HOST']}:{db['DB_PORT']}/{db['DB_NAME']}"
    }


def _resolve_runtime_env() -> dict[str, str]:
    """Pass through only allowed runtime environment variables."""
    return {
        key: os.getenv(key, "")
        for key in RUNTIME_ENV_WHITELIST
        if os.getenv(key) is not None
    }


def _build_task_environment() -> dict[str, str]:
    return {
        **_resolve_runtime_env(),
        **_resolve_database_env(),
    }


# ----------------------------
# DAG
# ----------------------------


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
        environment=_build_task_environment(),
        mount_tmp_dir=False,
        auto_remove="success",
        command=(
            "python -m competency_system.presentation.airflow.jobs.task_sync_runner "
            f'--start "{START_TEMPLATE}" '
            f'--end "{END_TEMPLATE}"'
        ),
    )


task_sync = task_sync_dag()
