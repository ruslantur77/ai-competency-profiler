from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from airflow.decorators import dag, task

from competency_system.application.use_cases.candidate import AssessCandidateUseCase
from competency_system.application.use_cases.ranking import RecalculateRankingUseCase
from competency_system.presentation.airflow.context import get_dag_conf
from competency_system.presentation.airflow.payloads import (
    CandidateAssessmentTriggerDTO,
)
from competency_system.presentation.airflow.runtime import run_logged_async

DEFAULT_ARGS = {
    "owner": "competency-system",
    "retries": 1,
}


@dag(
    dag_id="candidate_assessment",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["candidate", "assessment", "batch"],
)
def candidate_assessment_dag() -> None:
    @task(task_id="assess_candidate")
    def assess_candidate() -> dict[str, object]:
        payload = CandidateAssessmentTriggerDTO.model_validate(get_dag_conf())
        result = run_logged_async(
            "candidate_assessment.assess_candidate",
            lambda runtime: AssessCandidateUseCase(
                runtime.uow(),
                runtime.llm_gateway(),
            ).execute(payload)
        )
        return {
            "assessment": result.model_dump(mode="json"),
            "vacancy_id": str(payload.vacancy_id) if payload.vacancy_id else None,
        }

    @task(task_id="recalculate_ranking")
    def recalculate_ranking(payload: dict[str, object]) -> dict[str, object]:
        vacancy_id = payload.get("vacancy_id")
        if not vacancy_id:
            return {"skipped": True, "reason": "vacancy_id is not provided"}

        ranking = run_logged_async(
            "candidate_assessment.recalculate_ranking",
            lambda runtime: RecalculateRankingUseCase(
                runtime.uow(),
            ).execute(UUID(str(vacancy_id)))
        )
        return ranking.model_dump(mode="json")

    recalculate_ranking(assess_candidate())


candidate_assessment = candidate_assessment_dag()
