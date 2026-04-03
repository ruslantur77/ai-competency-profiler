from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from airflow.decorators import dag as airflow_dag  # type: ignore[attr-defined]
from airflow.decorators import task as airflow_task  # type: ignore[attr-defined]

from competency_system.application.use_cases.task import SyncTasksUseCase
from competency_system.presentation.airflow.runtime import run_logged_async

dag = cast(Any, airflow_dag)
task = cast(Any, airflow_task)

DEFAULT_ARGS = {
    "owner": "competency-system",
    "retries": 1,
}


@dag(
    dag_id="task_sync",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    schedule="@daily",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["tasks", "sync", "batch"],
)
def task_sync_dag() -> None:
    @task(task_id="sync_tasks")
    def sync_tasks() -> dict[str, object]:
        result = run_logged_async(
            "task_sync.sync_tasks",
            lambda runtime: SyncTasksUseCase(
                runtime.uow(),
                runtime.testing_gateway(),
                runtime.llm_gateway(),
                runtime.llm_job_queue(),
            ).execute(),
        )
        return result.model_dump(mode="json")

    sync_tasks()


task_sync = task_sync_dag()
