from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from competency_system.application.dtos.auth import CurrentUserDTO
from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.use_cases.candidate import AssessCandidateUseCase
from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    SubCompetency,
    Task,
    TaskCompetencyMapping,
    TestResult,
)
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import TaskType, UserRole
from competency_system.infrastructure.persistence.models import Base
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.presentation.api.dependencies import (
    get_current_user,
    get_llm_gateway,
    get_uow,
)
from competency_system.presentation.api.main import app


class FakeLLMGateway(LLMGateway):
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[list[LLMMessage]] = []

    async def generate(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        *,
        temperature: float = 0.2,
    ) -> BaseModel:
        self.calls.append(messages)
        return response_model.model_validate(self.response)


async def _make_session_factory(
    database_path: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _seed_competencies(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    competencies: list[Competency],
) -> None:
    category = Category(
        name="Backend",
        description="Backend systems",
        competencies=competencies,
    )
    for competency in category.competencies:
        competency.category_id = category.id

    async with SQLAlchemyUnitOfWork(session_factory) as uow:
        await uow.categories.add(category)
        await uow.commit()


async def _seed_task(
    session_factory: async_sessionmaker[AsyncSession],
    task: Task,
) -> None:
    async with SQLAlchemyUnitOfWork(session_factory) as uow:
        await uow.tasks.add(task)
        await uow.commit()


def test_candidate_scorer_uses_weighted_coverage() -> None:
    sub_critical = SubCompetency(name="Critical path", weight=0.7)
    sub_minor = SubCompetency(name="Minor path", weight=0.3)
    competency = Competency(
        category_id=UUID(int=1),
        name="API design",
        sub_competencies=[sub_critical, sub_minor],
    )
    candidate = Candidate(
        external_id="candidate-1",
        achieved_subcompetency_ids={sub_critical.id},
    )

    scorer = CandidateScorer()
    scores = scorer.calculate_scores(candidate, [competency])

    assert len(scores) == 1
    assert scores[0].level == CompetencyLevel.ADVANCED
    assert scores[0].confidence == pytest.approx(0.7)


def test_candidate_scorer_requires_sufficient_result_quality() -> None:
    sub_critical = SubCompetency(name="Critical path", weight=0.8)
    sub_minor = SubCompetency(name="Minor path", weight=0.2)
    task = Task(
        external_id="task-1",
        title="Build API",
        description="Implement endpoint",
        type=TaskType.TEST,
        competency_mappings=[
            TaskCompetencyMapping(sub_competency_id=sub_critical.id, weight=0.8),
            TaskCompetencyMapping(sub_competency_id=sub_minor.id, weight=0.2),
        ],
    )
    result = TestResult(
        candidate_id=uuid4(),
        task_id=task.id,
        passed=False,
        score=40.0,
        attempts=1,
    )

    scorer = CandidateScorer()
    achieved = scorer.calculate_achievements([result], [task])

    assert achieved == set()


@pytest.mark.asyncio
async def test_assess_candidate_rejects_invalid_llm_schema(tmp_path: Path) -> None:
    engine, session_factory = await _make_session_factory(
        str(tmp_path / "invalid_llm_test.db")
    )
    task = Task(
        external_id="task-1",
        title="Build API",
        description="Implement endpoint",
        type=TaskType.CODE,
        competency_mappings=[
            TaskCompetencyMapping(sub_competency_id=uuid4(), weight=1.0),
        ],
    )
    await _seed_task(session_factory, task)

    fake_llm = FakeLLMGateway({"feedback": "missing required fields"})
    use_case = AssessCandidateUseCase(SQLAlchemyUnitOfWork(session_factory), fake_llm)

    try:
        with pytest.raises(ValidationError):
            await use_case.execute(
                CandidateTaskAssessmentDTO(
                    candidate_external_id="candidate-1",
                    task_external_id="task-1",
                    type=TaskType.CODE,
                    code="print('hello')",
                    passed=3,
                    total=5,
                    attempts=1,
                    duration_seconds=30,
                )
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_candidate_profile_webhook_and_read_api(tmp_path: Path) -> None:
    engine, session_factory = await _make_session_factory(
        str(tmp_path / "candidate_flow_test.db")
    )

    sub_critical = SubCompetency(name="Critical path", weight=0.8)
    sub_minor = SubCompetency(name="Minor path", weight=0.2)
    await _seed_competencies(
        session_factory,
        competencies=[
            Competency(
                category_id=UUID(int=1),
                name="API design",
                sub_competencies=[sub_critical, sub_minor],
            ),
        ],
    )
    await _seed_task(
        session_factory,
        Task(
            external_id="task-1",
            title="Build API",
            description="Implement endpoint",
            type=TaskType.CODE,
            competency_mappings=[
                TaskCompetencyMapping(sub_competency_id=sub_critical.id, weight=0.8),
                TaskCompetencyMapping(sub_competency_id=sub_minor.id, weight=0.2),
            ],
        ),
    )

    fake_llm = FakeLLMGateway(
        {
            "passed": True,
            "score": 85.0,
            "feedback": "Solid implementation",
            "strengths": ["structure"],
            "issues": ["minor style"],
        }
    )

    def override_uow() -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(session_factory)

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_llm_gateway] = lambda: fake_llm
    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=UUID(int=1),
        role=UserRole.ADMIN,
    )

    try:
        with TestClient(app) as client:
            webhook_response = client.post(
                "/webhook/task-completed",
                json={
                    "candidate_external_id": "candidate-1",
                    "task_external_id": "task-1",
                    "type": "code",
                    "code": "print('hello')",
                    "passed": 3,
                    "total": 5,
                    "attempts": 1,
                    "duration_seconds": 30,
                },
            )
            assert webhook_response.status_code == 200
            payload = webhook_response.json()
            candidate_profile = payload["candidate_profile"]
            candidate_id = candidate_profile["candidate_id"]
            assert candidate_profile["external_id"] == "candidate-1"
            assert candidate_profile["total_score"] == pytest.approx(80.0)
            assert len(candidate_profile["competency_scores"]) == 1
            assert candidate_profile["competency_scores"][0][
                "confidence"
            ] == pytest.approx(0.8)
            assert payload["test_result"]["llm_assessment"] is not None

            profile_response = client.get(f"/candidates/{candidate_id}/profile")
            assert profile_response.status_code == 200
            profile = profile_response.json()
            assert profile["candidate_id"] == candidate_id
            assert profile["external_id"] == "candidate-1"
            assert profile["total_score"] == pytest.approx(80.0)
            assert len(profile["competency_scores"]) == 1
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
