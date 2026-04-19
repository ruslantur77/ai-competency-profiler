from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from competency_system.application.dtos.candidate import (
    CandidateAssessmentResultDTO,
    CandidateListItemDto,
    CandidateProfileDTO,
)
from competency_system.application.dtos.mappers import (
    candidate_profile_dto_from_scoring,
    test_result_dto_from_domain,
)
from competency_system.application.dtos.pagination import PaginatedItemsDTO
from competency_system.application.dtos.task import (
    CandidateTaskAssessmentDTO,
    LLMCodeAssessmentDTO,
)
from competency_system.application.dtos.webhooks import (
    WebhookEvent,
    WebhookEventPayload,
    WebhookEventStatus,
)
from competency_system.application.errors import ConflictError, NotFoundError
from competency_system.application.llm.llm_dispatch_payload import (
    CodeAssessmentPayload,
)
from competency_system.application.llm.prompts import PromptCatalog
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.ports.llm_jobs import LLMJobQueuePort, LLMJobType
from competency_system.application.ports.repositories import (
    CandidateInclude,
    TaskInclude,
    TestResultInclude,
    VacancyInclude,
)
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.entities import (
    Candidate,
    Task,
    TestResult,
    TestResultLLMAssessment,
    TestResultLLMFeedbackItem,
    TestResultQuestionAnswer,
)
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import AssessmentStatus, TaskType

logger = logging.getLogger(__name__)


class _DuplicateWebhookEvent(Exception):
    def __init__(self, result: CandidateAssessmentResultDTO) -> None:
        super().__init__("Duplicate webhook event")
        self.result = result


class WebhookEventOperation:
    """Отвечает за создание, обновление и идемпотентную проверку webhook-событий."""

    def __init__(self, uow: UnitOfWork, scorer: CandidateScorer) -> None:
        self._uow = uow
        self._scorer = scorer

    async def ensure_processing(self, command: CandidateTaskAssessmentDTO) -> None:
        """Создаёт событие со статусом PROCESSING.

        Поднимает _DuplicateWebhookEvent, если событие уже успешно обработано.
        Поднимает ValueError для любых других конфликтов.
        """
        async with self._uow as uow:
            existing = await uow.webhook_events.get_by_event_id(command.event_id)
            if existing is not None:
                await self._handle_existing(uow, existing, command)

            await uow.webhook_events.add(
                WebhookEvent(
                    id=uuid4(),
                    event_id=command.event_id,
                    vacancy_id=command.vacancy_id,
                    candidate_external_id=command.candidate_external_id,
                    task_external_id=command.task_external_id,
                    status=WebhookEventStatus.PROCESSING,
                    payload=WebhookEventPayload(data=command.model_dump(mode="json")),
                )
            )
            await uow.commit()

    async def mark_processed(
        self,
        command: CandidateTaskAssessmentDTO,
        *,
        candidate_id: UUID,
        test_result_id: UUID,
    ) -> None:
        await self._update(
            command,
            status=WebhookEventStatus.PROCESSED,
            error_message=None,
            candidate_id=candidate_id,
            test_result_id=test_result_id,
        )

    async def mark_failed(
        self, command: CandidateTaskAssessmentDTO, message: str
    ) -> None:
        await self._update(
            command, status=WebhookEventStatus.FAILED, error_message=message
        )

    async def _handle_existing(
        self,
        uow: UnitOfWork,
        existing: WebhookEvent,
        command: CandidateTaskAssessmentDTO,
    ) -> None:
        if existing.status == WebhookEventStatus.PROCESSING:
            raise ValueError(f"Webhook event {command.event_id} is processing")
        if existing.status != WebhookEventStatus.PROCESSED:
            raise ValueError(f"Webhook event {command.event_id} already handled")
        if existing.candidate_id is None or existing.test_result_id is None:
            raise ValueError("Stored webhook event references missing result")

        candidate = await uow.candidates.get(
            existing.candidate_id, include={CandidateInclude.ACHIEVEMENTS}
        )
        test_result = await uow.test_results.get(
            existing.test_result_id,
            include={
                TestResultInclude.QUESTION_ANSWERS,
                TestResultInclude.LLM_ASSESSMENT,
            },
        )
        if candidate is None or test_result is None:
            raise ValueError("Stored webhook event references missing result")

        vacancy = await uow.vacancies.get(
            existing.vacancy_id, include={VacancyInclude.NORMALIZED_GRAPH}
        )
        if vacancy is None:
            raise NotFoundError(f"Vacancy {existing.vacancy_id} not found")

        scores = self._scorer.calculate_scores(
            candidate, vacancy.requirement_competencies
        )
        category_names_by_id = {
            node.category_id: node.category.name if node.category else ""
            for node in vacancy.category_nodes
        }
        raise _DuplicateWebhookEvent(
            CandidateAssessmentResultDTO(
                candidate_profile=candidate_profile_dto_from_scoring(
                    candidate,
                    scores,
                    competencies=vacancy.requirement_competencies,
                    category_names_by_id=category_names_by_id,
                ),
                test_result=test_result_dto_from_domain(test_result),
            )
        )

    async def _update(
        self,
        command: CandidateTaskAssessmentDTO,
        *,
        status: WebhookEventStatus,
        **fields: Any,
    ) -> None:
        async with self._uow as uow:
            event = await uow.webhook_events.get_by_event_id(command.event_id)
            if event is None:
                return
            event.status = status
            event.processed_at = datetime.now(UTC)
            for key, value in fields.items():
                setattr(event, key, value)
            await uow.webhook_events.add(event)
            await uow.commit()


class LLMCodeAssessmentOperation:
    def __init__(
        self,
        uow: UnitOfWork,
        llm_gateway: LLMGateway | None = None,
        prompt_version: str = "v1",
    ) -> None:
        self._uow = uow
        self._llm_gateway = llm_gateway
        self._prompt_catalog = PromptCatalog()
        self.prompt_version = prompt_version

        scorer = CandidateScorer()
        self._webhook_op = WebhookEventOperation(uow, scorer)
        self._scoring_op = CandidateScoringOperation(uow, scorer, prompt_version)

    async def run(
        self,
        test_result_id: UUID,
        passed_tests: int,
        total_tests: int,
        duration_seconds: int,
    ) -> None:
        if self._llm_gateway is None:
            logger.info(
                "llm_operation_skipped",
                extra={
                    "operation": "code_assessment",
                    "reason": "llm_gateway_missing",
                    "test_result_id": str(test_result_id),
                },
            )
            return
        async with self._uow as uow:
            result = await uow.test_results.get(
                test_result_id,
                include={TestResultInclude.TASK, TestResultInclude.LLM_ASSESSMENT},
            )
            if result is None or result.task is None or not result.code_submitted:
                logger.info(
                    "llm_operation_skipped",
                    extra={
                        "operation": "code_assessment",
                        "reason": "test_result_not_ready",
                        "test_result_id": str(test_result_id),
                        "has_result": result is not None,
                        "has_task": bool(result and result.task),
                        "has_code": bool(result and result.code_submitted),
                    },
                )
                return
            try:
                assessment = await self._llm_gateway.generate(
                    [
                        LLMMessage(
                            role="system",
                            content=self._prompt_catalog.get_code_assessment_prompts(
                                self.prompt_version
                            ).prompt,
                        ),
                        LLMMessage(
                            role="user",
                            content=(
                                f"Task: {result.task.title}\n"
                                f"Description: {result.task.description}\n"
                                f"Candidate code:\n{result.code_submitted}\n\n"
                                f"Passed tests: {passed_tests}/{total_tests}\n"
                                f"Attempts: {result.attempts}\n"
                                f"Duration: {duration_seconds} seconds"
                            ),
                        ),
                    ],
                    LLMCodeAssessmentDTO,
                )
            except Exception as exc:
                logger.exception(
                    "llm_operation_failed",
                    extra={
                        "operation": "code_assessment",
                        "status": "failed",
                        "test_result_id": str(test_result_id),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                raise
        await self._scoring_op.apply_llm_assessment(test_result_id, assessment)
        logger.info(
            "llm_operation_finished",
            extra={
                "operation": "code_assessment",
                "status": "success",
                "test_result_id": str(test_result_id),
                "score": assessment.score,
                "passed": assessment.passed,
                "feedback_items_count": len(assessment.feedback_items),
                "feedback_items_sample": [
                    item.model_dump(mode="json")
                    for item in assessment.feedback_items[:3]
                ],
            },
        )


class CandidateScoringOperation:
    """Отвечает за оценку задания, обновление достижений кандидата и расчёт скоров."""

    def __init__(
        self,
        uow: UnitOfWork,
        scorer: CandidateScorer,
        prompt_version: str,
    ) -> None:
        self._uow = uow
        self._scorer = scorer
        self._prompt_version = prompt_version

    async def run(
        self, command: CandidateTaskAssessmentDTO
    ) -> tuple[Candidate, TestResult, CandidateAssessmentResultDTO]:
        async with self._uow as uow:
            candidate = await self._get_or_create_candidate(uow, command)

            task = await uow.tasks.get_by_external_id(
                command.task_external_id,
                include={TaskInclude.NORMALIZED_GRAPH},
            )
            if task is None:
                raise NotFoundError(f"Task {command.task_external_id} not found")

            test_result = self._build_test_result(command, task, candidate.id)

            candidate.achieved_subcompetency_ids |= self._scorer.calculate_achievements(
                [test_result], [task]
            )
            candidate.assessment_status = AssessmentStatus.COMPLETED
            candidate.last_assessment_at = datetime.now(UTC)
            await uow.candidates.add(candidate)
            await uow.test_results.add(test_result)

            vacancy = await uow.vacancies.get(
                command.vacancy_id, include={VacancyInclude.NORMALIZED_GRAPH}
            )
            if vacancy is None:
                raise NotFoundError(f"Vacancy {command.vacancy_id} not found")

            scores = self._scorer.calculate_scores(
                candidate, vacancy.requirement_competencies
            )
            category_names_by_id = {
                node.category_id: node.category.name if node.category else ""
                for node in vacancy.category_nodes
            }
            await uow.commit()

        result_dto = CandidateAssessmentResultDTO(
            candidate_profile=candidate_profile_dto_from_scoring(
                candidate,
                scores,
                competencies=vacancy.requirement_competencies,
                category_names_by_id=category_names_by_id,
            ),
            test_result=test_result_dto_from_domain(test_result),
        )
        return candidate, test_result, result_dto

    async def apply_llm_assessment(
        self,
        test_result_id: UUID,
        assessment: LLMCodeAssessmentDTO,
    ) -> None:
        async with self._uow as uow:
            result = await uow.test_results.get(
                test_result_id,
                include={TestResultInclude.LLM_ASSESSMENT},
            )
            if result is None:
                return

            base_raw = (
                result.llm_assessment.raw_test_score
                if result.llm_assessment
                else result.score
            )
            base_penalized = (
                result.llm_assessment.penalized_test_score
                if result.llm_assessment
                else result.score
            )
            final_score = max(base_penalized, assessment.score)

            result.score = final_score
            result.passed = bool(result.passed or assessment.passed)
            result.llm_assessment = TestResultLLMAssessment(
                id=result.llm_assessment.id if result.llm_assessment else uuid4(),
                test_result_id=result.id,
                passed=result.passed,
                score=assessment.score,
                feedback=assessment.feedback,
                criteria_version=self._prompt_version,
                raw_test_score=base_raw,
                penalized_test_score=base_penalized,
                attempt_penalty_applied=result.attempts > 1,
                final_score=final_score,
                feedback_items=[
                    TestResultLLMFeedbackItem(
                        id=uuid4(),
                        assessment_id=UUID(int=0),
                        type=item.type,
                        value=item.value,
                        position=index,
                    )
                    for index, item in enumerate(assessment.feedback_items)
                ],
            )
            await uow.test_results.add(result)
            await uow.commit()

    @staticmethod
    async def _get_or_create_candidate(
        uow: UnitOfWork, command: CandidateTaskAssessmentDTO
    ) -> Candidate:
        candidate = await uow.candidates.get_by_external_id(
            command.candidate_external_id,
            include={CandidateInclude.ACHIEVEMENTS},
            include_deleted=True,
        )
        if candidate is None:
            return Candidate(
                id=uuid4(),
                external_id=command.candidate_external_id,
                vacancy_id=command.vacancy_id,
            )
        if candidate.deleted_at is not None:
            raise ConflictError("Candidate is deleted")
        if candidate.vacancy_id != command.vacancy_id:
            raise ConflictError("Candidate is already assigned to another vacancy")
        return candidate

    def _build_test_result(
        self,
        command: CandidateTaskAssessmentDTO,
        task: Task,
        candidate_id: UUID,
    ) -> TestResult:
        raw = self._raw_score(command.passed, command.total)
        penalized = self._penalized_score(raw, command.attempts)
        passed = (
            command.passed > 0 and command.total > 0 and command.passed >= command.total
        )

        return TestResult(
            id=uuid4(),
            candidate_id=candidate_id,
            task_id=task.id,
            passed=passed,
            score=penalized,
            attempts=command.attempts,
            code_submitted=command.code,
            question_answers=[
                TestResultQuestionAnswer(
                    id=uuid4(),
                    test_result_id=UUID(int=0),
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    position=index,
                )
                for index, item in enumerate(command.question_answers)
            ],
            llm_assessment=TestResultLLMAssessment(
                id=uuid4(),
                test_result_id=UUID(int=0),
                passed=passed,
                score=penalized,
                feedback="",
                criteria_version=self._prompt_version,
                raw_test_score=raw,
                penalized_test_score=penalized,
                attempt_penalty_applied=command.attempts > 1,
                final_score=penalized,
                feedback_items=[],
            ),
        )

    @staticmethod
    def _raw_score(passed: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, passed / total * 100.0))

    @staticmethod
    def _penalized_score(score: float, attempts: int) -> float:
        return max(0.0, min(100.0, score)) * (0.9 ** max(0, attempts - 1))


# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------


class AssessCandidateUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        job_queue: LLMJobQueuePort,
        llm_gateway: LLMGateway | None = None,
        prompt_version: str = "v1",
    ) -> None:
        self._uow = uow
        self._job_queue = job_queue
        self._llm_gateway = llm_gateway
        self._prompt_catalog = PromptCatalog()
        self.prompt_version = prompt_version

        scorer = CandidateScorer()
        self._webhook_op = WebhookEventOperation(uow, scorer)
        self._scoring_op = CandidateScoringOperation(uow, scorer, prompt_version)

    async def execute(
        self, command: CandidateTaskAssessmentDTO
    ) -> CandidateAssessmentResultDTO:
        try:
            await self._webhook_op.ensure_processing(command)
        except _DuplicateWebhookEvent as duplicate:
            return duplicate.result

        try:
            _, test_result, result = await self._scoring_op.run(command)
        except Exception as exc:
            await self._webhook_op.mark_failed(command, str(exc))
            raise

        await self._webhook_op.mark_processed(
            command,
            candidate_id=result.candidate_profile.candidate_id,
            test_result_id=result.test_result.id,
        )
        await self._maybe_enqueue_code_assessment(command, test_result.id)
        return result

    async def _maybe_enqueue_code_assessment(
        self, command: CandidateTaskAssessmentDTO, test_result_id: UUID
    ) -> None:
        if (
            command.type != TaskType.CODE
            or not command.code
            or self._llm_gateway is None
        ):
            return
        await self._job_queue.enqueue(
            job_type=LLMJobType.CANDIDATE_CODE_ASSESSMENT,
            payload=CodeAssessmentPayload(
                test_result_id=test_result_id,
                passed_tests=command.passed,
                total_tests=command.total,
                duration_seconds=command.duration_seconds,
            ).model_dump(mode="json"),
        )


class GetCandidateProfileUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._scorer = CandidateScorer()

    async def execute(self, candidate_id: UUID) -> CandidateProfileDTO:
        async with self._uow as uow:
            candidate = await uow.candidates.get(
                candidate_id,
                include={
                    CandidateInclude.ACHIEVEMENTS,
                    CandidateInclude.VACANCY,
                    CandidateInclude.VACANCY_SUBCOMPETENCIES,
                },
            )
            if candidate is None:
                raise NotFoundError(f"Candidate {candidate_id} not found")
            vacancy = await uow.vacancies.get(
                candidate.vacancy_id, include={VacancyInclude.NORMALIZED_GRAPH}
            )
            if vacancy is None:
                raise NotFoundError(f"Vacancy {candidate.vacancy_id} not found")

            scores = self._scorer.calculate_scores(
                candidate, vacancy.requirement_competencies
            )
            category_names_by_id = {
                node.category_id: node.category.name if node.category else ""
                for node in vacancy.category_nodes
            }
            return candidate_profile_dto_from_scoring(
                candidate,
                scores,
                competencies=vacancy.requirement_competencies,
                category_names_by_id=category_names_by_id,
            )


class ListVacancyCandidatesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> list[CandidateListItemDto]:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(vacancy_id)
            if vacancy is None:
                raise NotFoundError(f"Vacancy {vacancy_id} not found")
            candidates = await uow.candidates.list_by_vacancy(vacancy_id)
            return [
                CandidateListItemDto(
                    id=item.id,
                    external_id=item.external_id,
                    vacancy_id=item.vacancy_id,
                    status=item.status,
                    last_assessment_at=item.last_assessment_at,
                    deleted_at=item.deleted_at,
                )
                for item in candidates
            ]


class ListCandidatesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        *,
        limit: int,
        offset: int,
    ) -> PaginatedItemsDTO[CandidateListItemDto]:
        async with self._uow as uow:
            candidates = await uow.candidates.get_list(limit=limit, offset=offset)
            total = await uow.candidates.count()
            items = [
                CandidateListItemDto(
                    id=item.id,
                    external_id=item.external_id,
                    vacancy_id=item.vacancy_id,
                    status=item.status,
                    last_assessment_at=item.last_assessment_at,
                    deleted_at=item.deleted_at,
                )
                for item in candidates
            ]
            return PaginatedItemsDTO[CandidateListItemDto](
                items=items,
                total=total,
                limit=limit,
                offset=offset,
            )


class GetCandidateUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, candidate_id: UUID) -> CandidateListItemDto:
        async with self._uow as uow:
            candidate = await uow.candidates.get(candidate_id)
            if candidate is None:
                raise NotFoundError(f"Candidate {candidate_id} not found")
            return CandidateListItemDto(
                id=candidate.id,
                external_id=candidate.external_id,
                vacancy_id=candidate.vacancy_id,
                status=candidate.status,
                last_assessment_at=candidate.last_assessment_at,
                deleted_at=candidate.deleted_at,
            )


class DeleteCandidateUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, candidate_id: UUID) -> None:
        async with self._uow as uow:
            deleted = await uow.candidates.soft_delete(candidate_id)
            if deleted is None:
                raise NotFoundError(f"Candidate {candidate_id} not found")
            await uow.commit()
