from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from competency_system.application.llm_dispatch import dispatch_llm_job
from competency_system.application.llm_dispatch_payload import (
    CodeAssessmentPayload,
    VacancyExtractionPayload,
)
from competency_system.application.ports.llm_jobs import LLMJobType

pytestmark = pytest.mark.unit


async def test_dispatch_llm_job_calls_candidate_code_assessment_operation(
    mock_uow, llm_gateway_mock, monkeypatch
) -> None:
    run_mock = AsyncMock()

    class _FakeOperation:
        def __init__(self, uow, llm_gateway, prompt_version) -> None:  # type: ignore[no-untyped-def]
            self.uow = uow
            self.llm_gateway = llm_gateway
            self.prompt_version = prompt_version

        async def run(  # type: ignore[no-untyped-def]
            self, test_result_id, passed_tests, total_tests, duration_seconds
        ) -> None:
            await run_mock(test_result_id, passed_tests, total_tests, duration_seconds)

    monkeypatch.setattr(
        "competency_system.application.llm_dispatch.LLMCodeAssessmentOperation",
        _FakeOperation,
    )
    payload_model = CodeAssessmentPayload(
        test_result_id=uuid4(),
        passed_tests=7,
        total_tests=10,
        duration_seconds=120,
    )
    payload = payload_model.model_dump(mode="json")

    await dispatch_llm_job(
        LLMJobType.CANDIDATE_CODE_ASSESSMENT,
        payload,
        uow=mock_uow,
        llm_gateway=llm_gateway_mock,
        prompt_version="v1",
    )

    run_mock.assert_awaited_once_with(
        payload_model.test_result_id,
        payload_model.passed_tests,
        payload_model.total_tests,
        payload_model.duration_seconds,
    )


async def test_dispatch_llm_job_raises_for_unknown_job_type(
    mock_uow, llm_gateway_mock
) -> None:
    with pytest.raises(ValueError, match="Unknown job type"):
        await dispatch_llm_job(
            "unknown",  # type: ignore[arg-type]
            {},
            uow=mock_uow,
            llm_gateway=llm_gateway_mock,
            prompt_version="v1",
        )


async def test_dispatch_llm_job_accepts_vacancy_extraction_payload(
    mock_uow, llm_gateway_mock
) -> None:
    payload = VacancyExtractionPayload(
        vacancy_id=uuid4(),
        raw_text="Backend role",
    ).model_dump(mode="json")

    await dispatch_llm_job(
        LLMJobType.VACANCY_EXTRACTION,
        payload,
        uow=mock_uow,
        llm_gateway=llm_gateway_mock,
        prompt_version="v1",
    )
