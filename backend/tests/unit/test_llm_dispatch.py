from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from competency_system.application.llm.llm_dispatch import dispatch_llm_job
from competency_system.application.llm.llm_dispatch_payload import (
    CodeAssessmentPayload,
    TaskExtractionPayload,
    VacancyExtractionPayload,
)
from competency_system.application.ports.llm_jobs import LLMJobType

pytestmark = pytest.mark.unit


def _dispatch_kwargs() -> dict[str, object]:
    return {
        "vacancy_prompt_version": "v1",
        "task_prompt_version": "v1",
        "code_prompt_version": "v1",
        "max_parallel_requests": 4,
        "stage_timeout_seconds": 45.0,
        "max_suggested_new_per_stage": 5,
    }


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
        "competency_system.application.llm.llm_dispatch.LLMCodeAssessmentOperation",
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
        **_dispatch_kwargs(),
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
            **_dispatch_kwargs(),
        )


async def test_dispatch_llm_job_calls_vacancy_extraction_operation(
    mock_uow, llm_gateway_mock, monkeypatch
) -> None:
    run_mock = AsyncMock()

    class _FakeOperation:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            self.args = args
            self.kwargs = kwargs

        async def run(self, vacancy_id) -> None:  # type: ignore[no-untyped-def]
            await run_mock(vacancy_id)

    monkeypatch.setattr(
        "competency_system.application.llm.llm_dispatch.ExtractVacancyGraphOperation",
        _FakeOperation,
    )
    payload_model = VacancyExtractionPayload(
        vacancy_id=uuid4(),
        raw_text="Backend role",
    )
    payload = payload_model.model_dump(mode="json")

    await dispatch_llm_job(
        LLMJobType.VACANCY_EXTRACTION,
        payload,
        uow=mock_uow,
        llm_gateway=llm_gateway_mock,
        **_dispatch_kwargs(),
    )

    run_mock.assert_awaited_once_with(payload_model.vacancy_id)


async def test_dispatch_llm_job_calls_task_mapping_operation(
    mock_uow, llm_gateway_mock, monkeypatch
) -> None:
    run_mock = AsyncMock()

    class _FakeOperation:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            self.args = args
            self.kwargs = kwargs

        async def run(self, task_id) -> None:  # type: ignore[no-untyped-def]
            await run_mock(task_id)

    monkeypatch.setattr(
        "competency_system.application.llm.llm_dispatch.MapTaskToCompetenciesOperation",
        _FakeOperation,
    )
    payload_model = TaskExtractionPayload(
        task_id=uuid4(),
        raw_text="irrelevant",
    )
    payload = payload_model.model_dump(mode="json")

    await dispatch_llm_job(
        LLMJobType.TASK_MAPPING,
        payload,
        uow=mock_uow,
        llm_gateway=llm_gateway_mock,
        **_dispatch_kwargs(),
    )

    run_mock.assert_awaited_once_with(payload_model.task_id)
