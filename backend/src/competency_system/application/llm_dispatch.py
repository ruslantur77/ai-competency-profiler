from __future__ import annotations

from competency_system.application.llm_dispatch_payload import (
    CodeAssessmentPayload,
    VacancyExtractionPayload,
)
from competency_system.application.ports import LLMGateway, UnitOfWork
from competency_system.application.ports.llm_jobs import LLMJobType
from competency_system.application.use_cases.candidate import LLMCodeAssessmentOperation


async def dispatch_llm_job(
    job_type: LLMJobType,
    payload: dict[str, object],
    # dependencies
    uow: UnitOfWork,
    llm_gateway: LLMGateway,
    prompt_version: str,
) -> None:
    match job_type:
        case LLMJobType.CANDIDATE_CODE_ASSESSMENT:
            payload_model = CodeAssessmentPayload.model_validate(payload)
            op = LLMCodeAssessmentOperation(uow, llm_gateway, prompt_version)
            await op.run(
                test_result_id=payload_model.test_result_id,
                passed_tests=payload_model.passed_tests,
                total_tests=payload_model.total_tests,
                duration_seconds=payload_model.duration_seconds,
            )
            return
        case LLMJobType.VACANCY_EXTRACTION:
            payload_model = VacancyExtractionPayload.model_validate(payload)  # type: ignore
            ...
        case _:
            raise ValueError(f"Unknown job type: {job_type}")
