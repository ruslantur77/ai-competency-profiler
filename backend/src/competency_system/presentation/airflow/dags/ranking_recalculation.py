from __future__ import annotations

from datetime import UTC, datetime

from airflow.decorators import dag, task

from competency_system.application.use_cases.ranking import RecalculateRankingUseCase
from competency_system.presentation.airflow.context import get_dag_conf
from competency_system.presentation.airflow.payloads import (
    RankingRecalculationTriggerDTO,
)
from competency_system.presentation.airflow.runtime import run_logged_async

DEFAULT_ARGS = {
    "owner": "competency-system",
    "retries": 1,
}


@dag(
    dag_id="ranking_recalculation",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ranking", "batch"],
)
def ranking_recalculation_dag() -> None:
    @task(task_id="recalculate_ranking")
    def recalculate_ranking() -> dict[str, object]:
        payload = RankingRecalculationTriggerDTO.model_validate(get_dag_conf())
        result = run_logged_async(
            "ranking_recalculation.recalculate_ranking",
            lambda runtime: RecalculateRankingUseCase(runtime.uow()).execute(payload.vacancy_id)
        )
        return result.model_dump(mode="json")

    recalculate_ranking()


ranking_recalculation = ranking_recalculation_dag()
