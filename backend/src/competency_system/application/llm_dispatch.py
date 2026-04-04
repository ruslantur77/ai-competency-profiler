from __future__ import annotations

from competency_system.application.llm_dispatch_payload import (
    CodeAssessmentPayload,
    TaskExtractionPayload,
    VacancyExtractionPayload,
)
from competency_system.application.ports import LLMGateway, UnitOfWork
from competency_system.application.ports.llm_jobs import LLMJobType
from competency_system.application.use_cases.candidate import LLMCodeAssessmentOperation
from competency_system.application.use_cases.task import MapTaskToCompetenciesOperation
from competency_system.application.use_cases.vacancy import ExtractVacancyGraphOperation


async def dispatch_llm_job(
    job_type: LLMJobType,
    payload: dict[str, object],
    # dependencies
    uow: UnitOfWork,
    llm_gateway: LLMGateway,
    vacancy_prompt_version: str,
    task_prompt_version: str,
    code_prompt_version: str,
    max_parallel_requests: int,
    stage_timeout_seconds: float,
    max_suggested_new_per_stage: int,
) -> None:
    match job_type:
        case LLMJobType.CANDIDATE_CODE_ASSESSMENT:
            code_payload = CodeAssessmentPayload.model_validate(payload)
            code_operation = LLMCodeAssessmentOperation(
                uow, llm_gateway, code_prompt_version
            )
            await code_operation.run(
                test_result_id=code_payload.test_result_id,
                passed_tests=code_payload.passed_tests,
                total_tests=code_payload.total_tests,
                duration_seconds=code_payload.duration_seconds,
            )
            return
        case LLMJobType.VACANCY_EXTRACTION:
            vacancy_payload = VacancyExtractionPayload.model_validate(payload)
            vacancy_operation = ExtractVacancyGraphOperation(
                uow,
                llm_gateway,
                max_parallel_requests=max_parallel_requests,
                stage_timeout_seconds=stage_timeout_seconds,
                max_suggested_new_per_stage=max_suggested_new_per_stage,
                prompt_version=vacancy_prompt_version,
            )
            await vacancy_operation.run(vacancy_payload.vacancy_id)
            return
        case LLMJobType.TASK_MAPPING:
            task_payload = TaskExtractionPayload.model_validate(payload)
            task_operation = MapTaskToCompetenciesOperation(
                llm_gateway,
                uow,
                max_parallel_requests=max_parallel_requests,
                stage_timeout_seconds=stage_timeout_seconds,
                prompt_version=task_prompt_version,
            )
            await task_operation.run(task_payload.task_id)
            return
        case _:
            raise ValueError(f"Unknown job type: {job_type}")
