from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from competency_system.application.code_assessment_policy import (
    DEFAULT_CODE_ASSESSMENT_POLICY,
    CodeAssessmentPolicy,
)
from competency_system.application.dtos.candidate import (
    CandidateAssessmentResultDTO,
    CandidateProfileDTO,
    CompetencyScoreDTO,
)
from competency_system.application.dtos.task import (
    CandidateTaskAssessmentDTO,
    LLMCodeAssessmentDTO,
    TestResultDTO,
)
from competency_system.application.dtos.webhooks import (
    WebhookEvent,
    WebhookEventPayload,
    WebhookEventStatus,
)
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
    Competency,
    CompetencyScore,
    SubCompetency,
    Task,
    TestResult,
    TestResultLLMAssessment,
    TestResultLLMFeedbackItem,
    TestResultQuestionAnswer,
    Vacancy,
)
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import (
    AssessmentStatus,
    TaskType,
)


def _build_profile(
    candidate: Candidate,
    scores: list[CompetencyScore],
) -> CandidateProfileDTO:
    total_score = 0.0
    if scores:
        total_score = sum(score.confidence for score in scores) / len(scores) * 100
    return CandidateProfileDTO(
        candidate_id=candidate.id,
        external_id=candidate.external_id,
        competency_scores=[
            CompetencyScoreDTO(
                competency_id=score.competency_id,
                level=score.level,
                confidence=score.confidence,
            )
            for score in scores
        ],
        total_score=total_score,
    )


class AssessCandidateUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        job_queue: LLMJobQueuePort,
        llm_gateway: LLMGateway | None = None,
        code_policy: CodeAssessmentPolicy = DEFAULT_CODE_ASSESSMENT_POLICY,
    ) -> None:
        self._uow = uow
        self._job_queue = job_queue
        self._llm_gateway = llm_gateway
        self._scorer = CandidateScorer()
        self._code_policy = code_policy

    async def execute(
        self,
        command: CandidateTaskAssessmentDTO,
    ) -> CandidateAssessmentResultDTO:
        try:
            await self._ensure_processing_event(command)
        except _DuplicateWebhookEvent as duplicate:
            return duplicate.result
        try:
            result = await self._process_assessment(command)
            await self._mark_event_processed(
                command,
                candidate_id=result.candidate_profile.candidate_id,
                test_result_id=result.test_result.id,
            )
            return result
        except Exception as exc:
            await self._mark_event_failed(command, str(exc))
            raise

    async def _ensure_processing_event(
        self, command: CandidateTaskAssessmentDTO
    ) -> None:
        async with self._uow as uow:
            existing = await uow.webhook_events.get_by_event_id(command.event_id)
            if existing is not None:
                if (
                    existing.status == WebhookEventStatus.PROCESSED
                    and existing.candidate_id is not None
                    and existing.test_result_id is not None
                ):
                    candidate = await uow.candidates.get(
                        existing.candidate_id,
                        include={CandidateInclude.ACHIEVEMENTS},
                    )
                    test_result = await uow.test_results.get(
                        existing.test_result_id,
                        include={
                            TestResultInclude.QUESTION_ANSWERS,
                            TestResultInclude.LLM_ASSESSMENT,
                        },
                    )
                    if candidate is None or test_result is None:
                        raise ValueError(
                            "Stored webhook event references missing result"
                        )
                    vacancy_competencies = await self._get_vacancy_competencies(
                        uow, existing.vacancy_id
                    )
                    scores = self._scorer.calculate_scores(
                        candidate, vacancy_competencies
                    )
                    raise _DuplicateWebhookEvent(
                        CandidateAssessmentResultDTO(
                            candidate_profile=_build_profile(candidate, scores),
                            test_result=self._to_test_result_dto(test_result),
                        )
                    )
                if existing.status == WebhookEventStatus.PROCESSING:
                    raise ValueError(f"Webhook event {command.event_id} is processing")
                raise ValueError(f"Webhook event {command.event_id} already handled")

            event = WebhookEvent(
                id=uuid4(),
                event_id=command.event_id,
                vacancy_id=command.vacancy_id,
                candidate_external_id=command.candidate_external_id,
                task_external_id=command.task_external_id,
                status=WebhookEventStatus.PROCESSING,
                payload=WebhookEventPayload(data=command.model_dump(mode="json")),
            )
            await uow.webhook_events.add(event)
            await uow.commit()

    async def _process_assessment(
        self, command: CandidateTaskAssessmentDTO
    ) -> CandidateAssessmentResultDTO:
        async with self._uow as uow:
            candidate = await uow.candidates.get_by_external_id(
                command.candidate_external_id,
                include={CandidateInclude.ACHIEVEMENTS},
            )
            if candidate is None:
                candidate = Candidate(
                    id=uuid4(),
                    external_id=command.candidate_external_id,
                    vacancy_id=command.vacancy_id,
                )
            elif candidate.vacancy_id != command.vacancy_id:
                raise ValueError("Candidate is already assigned to another vacancy")

            task = await uow.tasks.get_by_external_id(
                command.task_external_id,
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
            )
            if task is None:
                raise ValueError(f"Task {command.task_external_id} not found")

            test_result = await self._assess_task(command, task, candidate.id)
            await uow.test_results.add(test_result)

            achievements = self._scorer.calculate_achievements(
                [test_result],
                [task],
            )
            candidate.achieved_subcompetency_ids |= achievements
            candidate.assessment_status = AssessmentStatus.COMPLETED
            candidate.last_assessment_at = datetime.now(UTC)
            await uow.candidates.add(candidate)

            vacancy_competencies = await self._get_vacancy_competencies(
                uow, command.vacancy_id
            )
            scores = self._scorer.calculate_scores(candidate, vacancy_competencies)
            await uow.commit()

            result = CandidateAssessmentResultDTO(
                candidate_profile=_build_profile(candidate, scores),
                test_result=self._to_test_result_dto(test_result),
            )
            if (
                command.type == TaskType.CODE
                and command.code
                and self._llm_gateway is not None
            ):
                await self._job_queue.enqueue(
                    # TODO: replace in-process runner with external queue producer.
                    job_type=LLMJobType.CANDIDATE_CODE_ASSESSMENT,
                    payload={"test_result_id": str(test_result.id)},
                    runner=lambda: self._process_code_assessment_job(
                        test_result.id,
                        command.passed,
                        command.total,
                        command.duration_seconds,
                    ),
                )
            return result

    async def _mark_event_processed(
        self,
        command: CandidateTaskAssessmentDTO,
        *,
        candidate_id: UUID,
        test_result_id: UUID,
    ) -> None:
        async with self._uow as uow:
            event = await uow.webhook_events.get_by_event_id(command.event_id)
            if event is None:
                return
            event.status = WebhookEventStatus.PROCESSED
            event.error_message = None
            event.candidate_id = candidate_id
            event.test_result_id = test_result_id
            event.processed_at = datetime.now(UTC)
            await uow.webhook_events.add(event)
            await uow.commit()

    async def _mark_event_failed(
        self,
        command: CandidateTaskAssessmentDTO,
        message: str,
    ) -> None:
        async with self._uow as uow:
            event = await uow.webhook_events.get_by_event_id(command.event_id)
            if event is None:
                return
            event.status = WebhookEventStatus.FAILED
            event.error_message = message
            event.processed_at = datetime.now(UTC)
            await uow.webhook_events.add(event)
            await uow.commit()

    async def _assess_task(
        self,
        command: CandidateTaskAssessmentDTO,
        task: Task,
        candidate_id: UUID,
    ) -> TestResult:
        raw_test_score = self._raw_test_score(command.passed, command.total)
        penalized_test_score = self._apply_attempt_penalty(
            raw_test_score, command.attempts
        )
        score = penalized_test_score
        passed = (
            command.passed > 0 and command.total > 0 and command.passed >= command.total
        )
        llm_assessment = TestResultLLMAssessment(
            id=uuid4(),
            test_result_id=UUID(int=0),
            passed=passed,
            score=score,
            feedback="",
            criteria_version=self._code_policy.version,
            raw_test_score=raw_test_score,
            penalized_test_score=penalized_test_score,
            attempt_penalty_applied=command.attempts > 1,
            final_score=score,
            feedback_items=[],
        )

        return TestResult(
            id=uuid4(),
            candidate_id=candidate_id,
            task_id=task.id,
            passed=passed,
            score=score,
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
            llm_assessment=llm_assessment,
        )

    async def _process_code_assessment_job(
        self,
        test_result_id: UUID,
        passed_tests: int,
        total_tests: int,
        duration_seconds: int,
    ) -> None:
        if self._llm_gateway is None:
            return
        async with self._uow as uow:
            result = await uow.test_results.get(
                test_result_id,
                include={TestResultInclude.TASK, TestResultInclude.LLM_ASSESSMENT},
            )
            if result is None or result.task is None or not result.code_submitted:
                return
            assessment = await self._llm_gateway.generate(
                [
                    LLMMessage(
                        role="system",
                        content=self._code_policy.system_prompt,
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
                criteria_version=self._code_policy.version,
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

    def _raw_test_score(self, passed: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, (passed / total) * 100.0))

    def _apply_attempt_penalty(self, score: float, attempts: int) -> float:
        base = max(0.0, min(100.0, score))
        return base * (0.9 ** max(0, attempts - 1))

    def _to_test_result_dto(self, result: TestResult) -> TestResultDTO:
        llm_assessment_payload: dict[str, object] | None
        if result.llm_assessment is None:
            llm_assessment_payload = None
        else:
            llm_assessment_payload = {
                "passed": result.llm_assessment.passed,
                "score": result.llm_assessment.score,
                "feedback": result.llm_assessment.feedback,
                "criteria_version": result.llm_assessment.criteria_version,
                "raw_test_score": result.llm_assessment.raw_test_score,
                "penalized_test_score": result.llm_assessment.penalized_test_score,
                "attempt_penalty_applied": result.llm_assessment.attempt_penalty_applied,  # noqa: E501
                "final_score": result.llm_assessment.final_score,
                "feedback_items": [
                    {
                        "type": item.type.value,
                        "value": item.value,
                        "position": item.position,
                    }
                    for item in result.llm_assessment.feedback_items
                ],
            }
        return TestResultDTO(
            id=result.id,
            candidate_id=result.candidate_id,
            task_id=result.task_id,
            passed=result.passed,
            score=result.score,
            attempts=result.attempts,
            code_submitted=result.code_submitted,
            question_answers=[
                {"question": item.question, "answer": item.answer}
                for item in result.question_answers
            ],
            llm_assessment=llm_assessment_payload,
            created_at=result.created_at,
        )

    async def _get_vacancy_competencies(
        self,
        uow: UnitOfWork,
        vacancy_id: UUID,
    ) -> list[Competency]:
        vacancy = await uow.vacancies.get(
            vacancy_id,
            include={VacancyInclude.NORMALIZED_GRAPH},
        )
        if vacancy is None:
            raise ValueError(f"Vacancy {vacancy_id} not found")
        return _build_requirement_competencies(vacancy)


# TODO: вынести эксепшн
class _DuplicateWebhookEvent(Exception):
    def __init__(self, result: CandidateAssessmentResultDTO) -> None:
        super().__init__("Duplicate webhook event")
        self.result = result


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
                raise ValueError(f"Candidate {candidate_id} not found")
            vacancy = await uow.vacancies.get(
                candidate.vacancy_id,
                include={VacancyInclude.NORMALIZED_GRAPH},
            )
            if vacancy is None:
                raise ValueError(f"Vacancy {candidate.vacancy_id} not found")
            scores = self._scorer.calculate_scores(
                candidate, _build_requirement_competencies(vacancy)
            )
            return _build_profile(candidate, scores)


def _build_requirement_competencies(vacancy: Vacancy) -> list[Competency]:
    competencies: list[Competency] = []
    sub_by_competency: dict[UUID, list[SubCompetency]] = {}
    for node in vacancy.sub_competency_nodes:
        base = node.sub_competency
        if base is None:
            continue
        sub_by_competency.setdefault(node.competency_id, []).append(
            SubCompetency(
                id=base.id,
                competency_id=base.competency_id,
                name=base.name,
                description=base.description,
                weight=node.weight,
                created_at=base.created_at,
                updated_at=base.updated_at,
            )
        )
    for node_competency in vacancy.competency_nodes:
        base_competency = node_competency.competency
        if base_competency is None:
            continue
        competencies.append(
            Competency(
                id=base_competency.id,
                category_id=base_competency.category_id,
                name=base_competency.name,
                description=base_competency.description,
                sub_competencies=sub_by_competency.get(
                    node_competency.competency_id, []
                ),
                created_at=base_competency.created_at,
                updated_at=base_competency.updated_at,
            )
        )
    return competencies
