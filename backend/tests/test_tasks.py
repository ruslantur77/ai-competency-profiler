from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from competency_system.application.dtos.task import (
    TaskMappingExtractionResultDTO,
)
from competency_system.application.dtos.auth import CurrentUserDTO
from competency_system.application.ports.external_testing_system import (
    ExternalTaskRecord,
    ExternalTestingSystemGateway,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.use_cases.task import (
    MapTaskToCompetenciesUseCase,
)
from competency_system.domain.entities import Category, Competency, SubCompetency, Task
from competency_system.domain.value_objects.enums import UserRole
from competency_system.domain.value_objects.enums import TaskType
from competency_system.infrastructure.persistence.models import Base
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.presentation.api.dependencies import (
    get_current_user,
    get_llm_gateway,
    get_testing_system_gateway,
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
        response_model: type[TaskMappingExtractionResultDTO],
        *,
        temperature: float = 0.2,
    ) -> TaskMappingExtractionResultDTO:
        self.calls.append(messages)
        return response_model.model_validate(self.response)


class FakeTestingGateway(ExternalTestingSystemGateway):
    def __init__(self, tasks: list[ExternalTaskRecord]) -> None:
        self._tasks = tasks

    async def list_tasks(self) -> list[ExternalTaskRecord]:
        return self._tasks


async def _seed_competencies(session_factory, subcompetencies: list[SubCompetency]) -> None:
    category = Category(
        name="Backend",
        description="Backend systems",
        competencies=[
            Competency(
                category_id=UUID(int=1),
                name="APIs",
                description="HTTP APIs",
                sub_competencies=subcompetencies,
            )
        ],
    )
    category.competencies[0].category_id = category.id

    async with SQLAlchemyUnitOfWork(session_factory) as uow:
        await uow.categories.add(category)
        await uow.commit()


def _make_session_factory(database_path: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    async def _setup() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        return engine, async_sessionmaker(engine, expire_on_commit=False)

    return asyncio.run(_setup())


@pytest.mark.asyncio
async def test_map_task_to_competencies_normalizes_response() -> None:
    sub1 = SubCompetency(name="Parsing JSON")
    sub2 = SubCompetency(name="Working with SQL")
    task = Task(
        external_id="task-1",
        title="Build API",
        description="Parse and store data",
        type=TaskType.CODE,
    )
    fake_llm = FakeLLMGateway(
        {
            "mappings": [
                {"sub_competency_id": str(sub1.id), "weight": 0.2},
                {"sub_competency_id": str(sub1.id), "weight": 0.3},
                {"sub_competency_id": str(sub2.id), "weight": 0.5},
                {"sub_competency_id": str(uuid4()), "weight": 1.0},
            ]
        }
    )

    use_case = MapTaskToCompetenciesUseCase(fake_llm)
    mappings = await use_case.execute(task, [sub1, sub2], tags=["api", "sql"])

    assert len(mappings) == 2
    assert {mapping.sub_competency_id for mapping in mappings} == {sub1.id, sub2.id}
    assert sum(mapping.weight for mapping in mappings) == pytest.approx(1.0)
    assert next(
        mapping.weight for mapping in mappings if mapping.sub_competency_id == sub1.id
    ) == pytest.approx(0.5)
    assert next(
        mapping.weight for mapping in mappings if mapping.sub_competency_id == sub2.id
    ) == pytest.approx(0.5)
    assert "api" in fake_llm.calls[0][1].content


@pytest.mark.asyncio
async def test_map_task_to_competencies_rejects_invalid_schema() -> None:
    sub1 = SubCompetency(name="Parsing JSON")
    task = Task(
        external_id="task-1",
        title="Build API",
        description="Parse and store data",
        type=TaskType.CODE,
    )
    fake_llm = FakeLLMGateway({})
    use_case = MapTaskToCompetenciesUseCase(fake_llm)

    with pytest.raises(ValidationError):
        await use_case.execute(task, [sub1], tags=[])


def test_task_sync_and_admin_mapping_flow(tmp_path) -> None:
    sub1 = SubCompetency(name="Parsing JSON")
    sub2 = SubCompetency(name="SQL access")
    engine, session_factory = _make_session_factory(str(tmp_path / "task_flow_test.db"))
    asyncio.run(_seed_competencies(session_factory, [sub1, sub2]))

    task_external_id = "task-sync-1"
    fake_testing_gateway = FakeTestingGateway(
        [
            ExternalTaskRecord(
                external_id=task_external_id,
                title="API task",
                description="Build and persist data",
                type=TaskType.CODE,
                tags=["json", "sql"],
            )
        ]
    )
    fake_llm = FakeLLMGateway(
        {
            "mappings": [
                {"sub_competency_id": str(sub1.id), "weight": 0.7},
                {"sub_competency_id": str(sub2.id), "weight": 0.3},
            ]
        }
    )

    def override_uow() -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(session_factory)

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_testing_system_gateway] = lambda: fake_testing_gateway
    app.dependency_overrides[get_llm_gateway] = lambda: fake_llm
    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=UUID(int=1),
        role=UserRole.ADMIN,
    )

    try:
        with TestClient(app) as client:
            sync_response = client.post("/tasks/sync")
            assert sync_response.status_code == 200
            payload = sync_response.json()
            assert len(payload["synced_tasks"]) == 1
            synced_task = payload["synced_tasks"][0]
            assert synced_task["external_id"] == task_external_id
            assert synced_task["mapping_validated"] is False
            assert len(synced_task["competency_mappings"]) == 2

            list_response = client.get("/admin/tasks")
            assert list_response.status_code == 200
            tasks = list_response.json()
            assert len(tasks) == 1
            task_id = tasks[0]["id"]

            detail_response = client.get(f"/admin/tasks/{task_id}")
            assert detail_response.status_code == 200
            assert detail_response.json()["external_id"] == task_external_id

            validate_response = client.post(f"/admin/tasks/{task_id}/mapping/validate")
            assert validate_response.status_code == 200
            assert validate_response.json()["mapping_validated"] is True

            rebuild_response = client.post(f"/admin/tasks/{task_id}/mapping/rebuild")
            assert rebuild_response.status_code == 200
            assert rebuild_response.json()["mapping_validated"] is False
            assert len(rebuild_response.json()["competency_mappings"]) == 2
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
