from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.use_cases.candidate import (
    AssessCandidateUseCase,
    _DuplicateWebhookEvent,
)
from competency_system.domain.value_objects.enums import TaskType
from tests.factories import ApiDTOFactory, TestResultFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def command() -> CandidateTaskAssessmentDTO:
    return CandidateTaskAssessmentDTO(
        event_id="evt-1",
        vacancy_id=uuid4(),
        candidate_external_id="candidate-1",
        task_external_id="task-1",
        type=TaskType.CODE,
        code="print('ok')",
        passed=10,
        total=10,
        attempts=1,
        duration_seconds=120,
    )


@pytest.fixture
def use_case(mock_uow, job_queue_mock, llm_gateway_mock):
    return AssessCandidateUseCase(
        mock_uow,
        job_queue_mock,
        llm_gateway=llm_gateway_mock,
        prompt_version="v1",
    )


async def test_assess_candidate_use_case_returns_result_and_enqueues_code_assessment(
    use_case: AssessCandidateUseCase,
    job_queue_mock,
    command: CandidateTaskAssessmentDTO,
) -> None:
    dto_factory = ApiDTOFactory()
    result_dto = dto_factory.make_candidate_result()
    test_result = TestResultFactory().make({"id": result_dto.test_result.id})
    use_case._webhook_op.ensure_processing = AsyncMock()
    use_case._webhook_op.mark_processed = AsyncMock()
    use_case._scoring_op.run = AsyncMock(return_value=(None, test_result, result_dto))

    result = await use_case.execute(command)

    assert (
        result.candidate_profile.candidate_id
        == result_dto.candidate_profile.candidate_id
    )
    use_case._webhook_op.ensure_processing.assert_awaited_once_with(command)
    use_case._webhook_op.mark_processed.assert_awaited_once()
    job_queue_mock.enqueue.assert_awaited_once()


async def test_assess_candidate_use_case_returns_cached_result_for_duplicate_event(
    use_case: AssessCandidateUseCase, command: CandidateTaskAssessmentDTO
) -> None:
    duplicate_result = ApiDTOFactory().make_candidate_result()
    use_case._webhook_op.ensure_processing = AsyncMock(
        side_effect=_DuplicateWebhookEvent(duplicate_result)
    )
    use_case._scoring_op.run = AsyncMock()

    result = await use_case.execute(command)

    assert result == duplicate_result
    use_case._scoring_op.run.assert_not_awaited()


async def test_assess_candidate_use_case_marks_failed_and_reraises_scoring_error(
    use_case: AssessCandidateUseCase, command: CandidateTaskAssessmentDTO
) -> None:
    use_case._webhook_op.ensure_processing = AsyncMock()
    use_case._webhook_op.mark_failed = AsyncMock()
    use_case._scoring_op.run = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await use_case.execute(command)

    use_case._webhook_op.mark_failed.assert_awaited_once_with(command, "boom")


async def test_assess_candidate_use_case_skips_enqueue_for_non_code_task(
    use_case: AssessCandidateUseCase,
    job_queue_mock,
    command: CandidateTaskAssessmentDTO,
) -> None:
    command.type = TaskType.TEST
    result_dto = ApiDTOFactory().make_candidate_result()
    test_result = TestResultFactory().make({"id": result_dto.test_result.id})
    use_case._webhook_op.ensure_processing = AsyncMock()
    use_case._webhook_op.mark_processed = AsyncMock()
    use_case._scoring_op.run = AsyncMock(return_value=(None, test_result, result_dto))

    await use_case.execute(command)

    job_queue_mock.enqueue.assert_not_awaited()


async def test_assess_candidate_use_case_skips_enqueue_for_empty_code(
    use_case: AssessCandidateUseCase,
    job_queue_mock,
    command: CandidateTaskAssessmentDTO,
) -> None:
    command.code = ""
    result_dto = ApiDTOFactory().make_candidate_result()
    test_result = TestResultFactory().make({"id": result_dto.test_result.id})
    use_case._webhook_op.ensure_processing = AsyncMock()
    use_case._webhook_op.mark_processed = AsyncMock()
    use_case._scoring_op.run = AsyncMock(return_value=(None, test_result, result_dto))

    await use_case.execute(command)

    job_queue_mock.enqueue.assert_not_awaited()


async def test_assess_candidate_use_case_skips_enqueue_when_gateway_missing(
    mock_uow, job_queue_mock, command: CandidateTaskAssessmentDTO
) -> None:
    use_case = AssessCandidateUseCase(mock_uow, job_queue_mock, llm_gateway=None)
    result_dto = ApiDTOFactory().make_candidate_result()
    test_result = TestResultFactory().make({"id": result_dto.test_result.id})
    use_case._webhook_op.ensure_processing = AsyncMock()
    use_case._webhook_op.mark_processed = AsyncMock()
    use_case._scoring_op.run = AsyncMock(return_value=(None, test_result, result_dto))

    await use_case.execute(command)

    job_queue_mock.enqueue.assert_not_awaited()
