from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from competency_system.application.dtos.task import LLMCodeAssessmentDTO
from competency_system.application.use_cases.candidate import LLMCodeAssessmentOperation
from tests.factories import TaskFactory, TestResultFactory

pytestmark = pytest.mark.unit


async def test_llm_code_assessment_operation_noops_when_gateway_missing(
    mock_uow,
) -> None:
    operation = LLMCodeAssessmentOperation(mock_uow, llm_gateway=None)

    await operation.run(TestResultFactory().make().id, 1, 1, 60)

    mock_uow.test_results.get.assert_not_awaited()


async def test_llm_code_assessment_operation_applies_gateway_assessment(
    mock_uow, llm_gateway_mock
) -> None:
    operation = LLMCodeAssessmentOperation(mock_uow, llm_gateway=llm_gateway_mock)
    operation._scoring_op.apply_llm_assessment = AsyncMock()
    task = TaskFactory().make({"title": "API", "description": "Build API"})
    result = TestResultFactory().make(
        {"task_id": task.id, "code_submitted": "print(1)"}
    )
    result.task = task
    mock_uow.test_results.get.return_value = result
    llm_gateway_mock.generate.return_value = LLMCodeAssessmentDTO(
        passed=True,
        score=80.0,
        feedback="good",
    )

    await operation.run(result.id, 7, 10, 120)

    llm_gateway_mock.generate.assert_awaited_once()
    operation._scoring_op.apply_llm_assessment.assert_awaited_once_with(
        result.id, llm_gateway_mock.generate.return_value
    )
