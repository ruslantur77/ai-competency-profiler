from __future__ import annotations

from datetime import UTC, datetime

from airflow.decorators import dag, task

from competency_system.application.use_cases.vacancy import ExtractVacancyGraphUseCase
from competency_system.presentation.airflow.context import get_dag_conf
from competency_system.presentation.airflow.payloads import VacancyExtractionPayloadDTO
from competency_system.presentation.airflow.runtime import run_logged_async

DEFAULT_ARGS = {
    "owner": "competency-system",
    "retries": 1,
}


@dag(
    dag_id="vacancy_extraction",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["vacancy", "llm", "batch"],
)
def vacancy_extraction_dag() -> None:
    @task(task_id="extract_vacancy_graph")
    def extract_vacancy_graph() -> dict[str, object]:
        payload = VacancyExtractionPayloadDTO.model_validate(get_dag_conf())
        result = run_logged_async(
            "vacancy_extraction.extract_vacancy_graph",
            lambda runtime: ExtractVacancyGraphUseCase(
                runtime.uow(),
                runtime.llm_gateway(),
                max_parallel_requests=runtime.settings.llm_max_parallel_requests,
                stage_timeout_seconds=runtime.settings.llm_stage_timeout_seconds,
            ).execute(payload)
        )
        return result.model_dump(mode="json")

    extract_vacancy_graph()


vacancy_extraction = vacancy_extraction_dag()
