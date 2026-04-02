from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from competency_system.application.ports.repositories import (
    TaskInclude,
    TestResultInclude,
)
from competency_system.application.ports.repositories import (
    TaskRepository as ITaskRepository,
)
from competency_system.application.ports.repositories import (
    TestResultRepository as ITestResultRepository,
)
from competency_system.domain.entities import Task, TestResult
from competency_system.infrastructure.persistence.mappers import (
    task_from_orm,
    task_to_orm,
    test_result_from_orm,
    test_result_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    TaskOrm,
    TaskSubCompetencyMappingOrm,
    TestResultOrm,
    TestResultQuestionAnswerOrm,
)
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
    normalize_include,
)


class TaskRepository(SQLAlchemyRepository[Task, TaskOrm, TaskInclude], ITaskRepository):
    model = TaskOrm

    def load_options(
        self,
        include: Collection[TaskInclude] | None = None,
    ) -> Sequence[Any]:
        includes = normalize_include(include)
        options: list[Any] = []
        if TaskInclude.SUB_COMPETENCY_MAPPINGS in includes:
            options.append(selectinload(TaskOrm.sub_competency_mappings))
        return tuple(options)

    async def get_by_external_id(
        self,
        external_id: str,
        *,
        include: Collection[TaskInclude] | None = None,
    ) -> Task | None:
        statement = (
            select(self.model)
            .where(TaskOrm.external_id == external_id)
            .options(*self.load_options(include))
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        task = self.to_domain(model)
        return task

    async def add(self, entity: Task) -> None:
        async with self._session.begin_nested():
            await super().add(entity)

            await self._session.execute(
                delete(TaskSubCompetencyMappingOrm).where(
                    TaskSubCompetencyMappingOrm.task_id == entity.id
                )
            )
            for position, mapping in enumerate(entity.sub_competency_mappings):
                self._session.add(
                    TaskSubCompetencyMappingOrm(
                        task_id=entity.id,
                        sub_competency_id=mapping.sub_competency_id,
                        weight=mapping.weight,
                        position=position,
                    )
                )
            await self._session.flush()

    def to_domain(self, model: TaskOrm) -> Task:
        return task_from_orm(model)

    def to_model(self, entity: Task) -> TaskOrm:
        return task_to_orm(entity)


class TestResultRepository(
    SQLAlchemyRepository[TestResult, TestResultOrm, TestResultInclude],
    ITestResultRepository,
):
    model = TestResultOrm

    def load_options(
        self,
        include: Collection[TestResultInclude] | None = None,
    ) -> Sequence[Any]:
        includes = normalize_include(include)
        options: list[Any] = []
        if TestResultInclude.CANDIDATE in includes:
            options.append(selectinload(TestResultOrm.candidate))
        if TestResultInclude.LLM_ASSESSMENT in includes:
            options.append(selectinload(TestResultOrm.llm_assessment))
        if TestResultInclude.QUESTION_ANSWERS in includes:
            options.append(selectinload(TestResultOrm.question_answers))
        if TestResultInclude.TASK in includes:
            options.append(selectinload(TestResultOrm.task))
        return tuple(options)

    async def add(self, entity: TestResult) -> None:
        await super().add(entity)

        await self._session.execute(
            delete(TestResultQuestionAnswerOrm).where(
                TestResultQuestionAnswerOrm.test_result_id == entity.id
            )
        )

        await self._session.flush()

    def to_domain(self, model: TestResultOrm) -> TestResult:
        return test_result_from_orm(model)

    def to_model(self, entity: TestResult) -> TestResultOrm:
        return test_result_to_orm(entity)
