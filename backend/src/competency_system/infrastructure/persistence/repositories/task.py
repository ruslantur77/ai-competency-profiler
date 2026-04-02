from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from competency_system.application.ports.repositories import (
    TaskInclude,
    TestResultInclude,
)
from competency_system.domain.entities import Task, TaskSubCompetencyMapping, TestResult
from competency_system.infrastructure.persistence.mappers import (
    task_from_orm,
    task_to_orm,
    test_result_from_orm,
    test_result_llm_assessment_from_rows,
    test_result_question_answer_from_row,
    test_result_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    TaskOrm,
    TaskSubCompetencyMappingOrm,
    TestResultLLMAssessmentOrm,
    TestResultLLMFeedbackOrm,
    TestResultOrm,
    TestResultQuestionAnswerOrm,
)
from competency_system.infrastructure.persistence.repositories.base import (
    SQLAlchemyRepository,
    normalize_include,
)


class TaskRepository(SQLAlchemyRepository[Task, TaskOrm]):
    model = TaskOrm

    def load_options(
        self,
        include: Collection[TaskInclude] | None = None,
    ) -> Sequence[Any]:
        includes = normalize_include(include)
        options: list[Any] = []
        if TaskInclude.SUB_COMPETENCY_MAPPINGS in includes:
            options.append(selectinload(TaskOrm.sub_competency_mappings))
        if TaskInclude.TEST_RESULTS in includes:
            options.append(selectinload(TaskOrm.test_results))
        return tuple(options)

    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[TaskInclude] | None = None,
    ) -> Task | None:
        model = await self._session.get(
            self.model,
            entity_id,
            options=list(self.load_options(include)),
        )
        if model is None:
            return None
        task = self.to_domain(model)
        if TaskInclude.SUB_COMPETENCY_MAPPINGS in normalize_include(include):
            task.sub_competency_mappings = self._mappings_from_orm(model)
        return task

    async def get_list(
        self,
        *,
        include: Collection[TaskInclude] | None = None,
    ) -> Sequence[Task]:
        statement = select(self.model).options(*self.load_options(include))
        result = await self._session.scalars(statement)
        rows = result.all()
        includes = normalize_include(include)
        tasks: list[Task] = []
        for row in rows:
            task = self.to_domain(row)
            if TaskInclude.SUB_COMPETENCY_MAPPINGS in includes:
                task.sub_competency_mappings = self._mappings_from_orm(row)
            tasks.append(task)
        return tasks

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
        if TaskInclude.SUB_COMPETENCY_MAPPINGS in normalize_include(include):
            task.sub_competency_mappings = self._mappings_from_orm(model)
        return task

    async def add(self, entity: Task) -> None:
        async with self._session.begin_nested():
            model = self.to_model(entity)
            await self._session.merge(model)
            await self._session.flush()

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

    def _mappings_from_orm(self, model: TaskOrm) -> list[TaskSubCompetencyMapping]:
        rows = sorted(model.sub_competency_mappings, key=lambda item: item.position)
        return [
            TaskSubCompetencyMapping(
                id=row.id,
                task_id=row.task_id,
                sub_competency_id=row.sub_competency_id,
                weight=row.weight,
                position=row.position,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for row in rows
        ]


class TestResultRepository(
    SQLAlchemyRepository[TestResult, TestResultOrm],
):
    model = TestResultOrm

    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[TestResultInclude] | None = None,
    ) -> TestResult | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        return await self._hydrate_result(model, include=include)

    async def get_list(
        self,
        *,
        include: Collection[TestResultInclude] | None = None,
    ) -> Sequence[TestResult]:
        result = await self._session.scalars(select(self.model))
        rows = result.all()
        return [await self._hydrate_result(row, include=include) for row in rows]

    async def add(self, entity: TestResult) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

        await self._session.execute(
            delete(TestResultQuestionAnswerOrm).where(
                TestResultQuestionAnswerOrm.test_result_id == entity.id
            )
        )
        for answer in entity.question_answers:
            self._session.add(
                TestResultQuestionAnswerOrm(
                    test_result_id=entity.id,
                    question=answer.question,
                    answer=answer.answer,
                    position=answer.position,
                )
            )

        existing_assessment = await self._session.scalar(
            select(TestResultLLMAssessmentOrm).where(
                TestResultLLMAssessmentOrm.test_result_id == entity.id
            )
        )
        if existing_assessment is not None:
            await self._session.execute(
                delete(TestResultLLMFeedbackOrm).where(
                    TestResultLLMFeedbackOrm.assessment_id == existing_assessment.id
                )
            )
            await self._session.delete(existing_assessment)
            await self._session.flush()

        if entity.llm_assessment is not None:
            llm = entity.llm_assessment
            assessment = TestResultLLMAssessmentOrm(
                test_result_id=entity.id,
                passed=llm.passed,
                score=llm.score,
                feedback=llm.feedback,
                criteria_version=llm.criteria_version,
                raw_test_score=llm.raw_test_score,
                penalized_test_score=llm.penalized_test_score,
                attempt_penalty_applied=llm.attempt_penalty_applied,
                final_score=llm.final_score,
            )
            self._session.add(assessment)
            await self._session.flush()

            for feedback_item in llm.feedback_items:
                self._session.add(
                    TestResultLLMFeedbackOrm(
                        assessment_id=assessment.id,
                        type=feedback_item.type,
                        value=feedback_item.value,
                        position=feedback_item.position,
                    )
                )

        await self._session.flush()

    def to_domain(self, model: TestResultOrm) -> TestResult:
        return test_result_from_orm(model)

    def to_model(self, entity: TestResult) -> TestResultOrm:
        return test_result_to_orm(entity)

    async def _hydrate_result(
        self,
        model: TestResultOrm,
        *,
        include: Collection[TestResultInclude] | None,
    ) -> TestResult:
        includes = normalize_include(include)
        entity = self.to_domain(model)

        if TestResultInclude.QUESTION_ANSWERS in includes:
            answers = (
                await self._session.scalars(
                    select(TestResultQuestionAnswerOrm)
                    .where(TestResultQuestionAnswerOrm.test_result_id == model.id)
                    .order_by(TestResultQuestionAnswerOrm.position)
                )
            ).all()
            entity.question_answers = [
                test_result_question_answer_from_row(row) for row in answers
            ]

        if TestResultInclude.LLM_ASSESSMENT in includes:
            assessment = await self._session.scalar(
                select(TestResultLLMAssessmentOrm).where(
                    TestResultLLMAssessmentOrm.test_result_id == model.id
                )
            )
            if assessment is not None:
                feedback_items = (
                    await self._session.scalars(
                        select(TestResultLLMFeedbackOrm)
                        .where(TestResultLLMFeedbackOrm.assessment_id == assessment.id)
                        .order_by(TestResultLLMFeedbackOrm.position)
                    )
                ).all()
                entity.llm_assessment = test_result_llm_assessment_from_rows(
                    assessment,
                    feedback_items=list(feedback_items),
                )
            else:
                entity.llm_assessment = None

        return entity
