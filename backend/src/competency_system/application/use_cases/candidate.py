from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

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
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.ports.uow import UnitOfWork
from competency_system.application.use_cases.code_assessment_policy import (
    DEFAULT_CODE_ASSESSMENT_POLICY,
    CodeAssessmentPolicy,
)
from competency_system.domain.entities import (
    Candidate,
    CompetencyScore,
    Task,
    TestResult,
)
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import AssessmentStatus, TaskType


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
        llm_gateway: LLMGateway | None = None,
        code_policy: CodeAssessmentPolicy = DEFAULT_CODE_ASSESSMENT_POLICY,
    ) -> None:
        self._uow = uow
        self._llm_gateway = llm_gateway
        self._scorer = CandidateScorer()
        self._code_policy = code_policy

    async def execute(
        self,
        command: CandidateTaskAssessmentDTO,
    ) -> CandidateAssessmentResultDTO:
        async with self._uow as uow:
            candidate = await uow.candidates.get_by_external_id(
                command.candidate_external_id
            )
            if candidate is None:
                candidate = Candidate(
                    id=uuid4(),
                    external_id=command.candidate_external_id,
                )

            task = await uow.tasks.get_by_external_id(command.task_external_id)
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

            competencies = await uow.competencies.list()
            scores = self._scorer.calculate_scores(candidate, list(competencies))
            await uow.commit()

            return CandidateAssessmentResultDTO(
                candidate_profile=_build_profile(candidate, scores),
                test_result=self._to_test_result_dto(test_result),
            )

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
        llm_assessment: dict[str, object] | None = None

        if (
            command.type == TaskType.CODE
            and command.code
            and self._llm_gateway is not None
        ):
            assessment = await self._llm_gateway.generate(
                [
                    LLMMessage(
                        role="system",
                        content=self._code_policy.system_prompt,
                    ),
                    LLMMessage(
                        role="user",
                        content=(
                            f"Task: {task.title}\n"
                            f"Description: {task.description}\n"
                            f"Candidate code:\n{command.code}\n\n"
                            f"Passed tests: {command.passed}/{command.total}\n"
                            f"Attempts: {command.attempts}\n"
                            f"Duration: {command.duration_seconds} seconds"
                        ),
                    ),
                ],
                LLMCodeAssessmentDTO,
            )
            score = max(penalized_test_score, assessment.score)
            passed = assessment.passed or passed
            llm_assessment = {
                **assessment.model_dump(),
                "criteria_version": self._code_policy.version,
                "raw_test_score": raw_test_score,
                "penalized_test_score": penalized_test_score,
                "attempt_penalty_applied": command.attempts > 1,
                "final_score": score,
            }
        else:
            llm_assessment = {
                "criteria_version": self._code_policy.version,
                "raw_test_score": raw_test_score,
                "penalized_test_score": penalized_test_score,
                "attempt_penalty_applied": command.attempts > 1,
                "final_score": score,
            }

        return TestResult(
            id=uuid4(),
            candidate_id=candidate_id,
            task_id=task.id,
            passed=passed,
            score=score,
            attempts=command.attempts,
            code_submitted=command.code,
            llm_assessment=llm_assessment,
        )

    def _raw_test_score(self, passed: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, (passed / total) * 100.0))

    def _apply_attempt_penalty(self, score: float, attempts: int) -> float:
        base = max(0.0, min(100.0, score))
        return base * (0.9 ** max(0, attempts - 1))

    def _to_test_result_dto(self, result: TestResult) -> TestResultDTO:
        return TestResultDTO(
            id=result.id,
            candidate_id=result.candidate_id,
            task_id=result.task_id,
            passed=result.passed,
            score=result.score,
            attempts=result.attempts,
            code_submitted=result.code_submitted,
            llm_assessment=result.llm_assessment,
            created_at=result.created_at,
        )


class GetCandidateProfileUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._scorer = CandidateScorer()

    async def execute(self, candidate_id: UUID) -> CandidateProfileDTO:
        async with self._uow as uow:
            candidate = await uow.candidates.get(candidate_id)
            if candidate is None:
                raise ValueError(f"Candidate {candidate_id} not found")
            competencies = await uow.competencies.list()
            scores = self._scorer.calculate_scores(candidate, list(competencies))
            return _build_profile(candidate, scores)
