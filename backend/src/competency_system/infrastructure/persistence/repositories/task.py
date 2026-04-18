from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
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
from competency_system.domain.entities import (
    Category,
    Competency,
    Task,
    TaskCategoryNode,
    TaskCompetencyNode,
    TaskSubCompetencyNode,
    TestResult,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import TaskStatus
from competency_system.infrastructure.persistence.mappers import (
    task_from_orm,
    task_to_orm,
    test_result_from_orm,
)
from competency_system.infrastructure.persistence.mappers import (
    test_result_to_orm as test_result_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    CategoryOrm,
    CompetencyOrm,
    SubCompetencyOrm,
    TaskCategoryNodeOrm,
    TaskCompetencyNodeOrm,
    TaskOrm,
    TaskSubCompetencyNodeOrm,
)
from competency_system.infrastructure.persistence.models import (
    TestResultLLMAssessmentOrm as TestResultLLMAssessmentOrm,
)
from competency_system.infrastructure.persistence.models import (
    TestResultLLMFeedbackOrm as TestResultLLMFeedbackOrm,
)
from competency_system.infrastructure.persistence.models import (
    TestResultOrm as TestResultOrm,
)
from competency_system.infrastructure.persistence.models import (
    TestResultQuestionAnswerOrm as TestResultQuestionAnswerOrm,
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
        if TaskInclude.NORMALIZED_GRAPH in includes:
            options.extend(
                [
                    selectinload(TaskOrm.category_nodes),
                    selectinload(TaskOrm.competency_nodes),
                    selectinload(TaskOrm.sub_competency_nodes),
                ]
            )
        return tuple(options)

    async def get(
        self,
        entity_id: UUID,
        *,
        include: Collection[TaskInclude] | None = None,
    ) -> Task | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        task = self.to_domain(model)
        includes = normalize_include(include)
        if TaskInclude.NORMALIZED_GRAPH in includes:
            (
                task.category_nodes,
                task.competency_nodes,
                task.sub_competency_nodes,
            ) = await self._load_normalized_graph(task.id)
        return task

    async def get_list(
        self,
        *,
        include: Collection[TaskInclude] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[Task]:
        statement = select(self.model).order_by(TaskOrm.created_at.desc())
        if offset > 0:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        tasks = [self.to_domain(model) for model in result.all()]
        includes = normalize_include(include)
        if TaskInclude.NORMALIZED_GRAPH in includes:
            for task in tasks:
                (
                    task.category_nodes,
                    task.competency_nodes,
                    task.sub_competency_nodes,
                ) = await self._load_normalized_graph(task.id)
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
        includes = normalize_include(include)
        if TaskInclude.NORMALIZED_GRAPH in includes:
            (
                task.category_nodes,
                task.competency_nodes,
                task.sub_competency_nodes,
            ) = await self._load_normalized_graph(task.id)
        return task

    async def list_by_statuses(
        self,
        statuses: set[TaskStatus] | None = None,
        *,
        include: Collection[TaskInclude] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[Task]:
        statement = select(self.model).order_by(TaskOrm.created_at.desc())
        if statuses:
            statement = statement.where(TaskOrm.status.in_(statuses))
        if offset > 0:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        tasks = [self.to_domain(model) for model in result.all()]
        includes = normalize_include(include)
        if TaskInclude.NORMALIZED_GRAPH in includes:
            for task in tasks:
                (
                    task.category_nodes,
                    task.competency_nodes,
                    task.sub_competency_nodes,
                ) = await self._load_normalized_graph(task.id)
        return tasks

    async def count_by_statuses(self, statuses: set[TaskStatus] | None = None) -> int:
        statement = select(func.count()).select_from(TaskOrm)
        if statuses:
            statement = statement.where(TaskOrm.status.in_(statuses))
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def add(self, entity: Task) -> None:
        async with self._session.begin_nested():
            await super().add(entity)
            await self._replace_normalized_graph(entity)

    async def _replace_normalized_graph(self, task: Task) -> None:
        await self._session.execute(
            delete(TaskSubCompetencyNodeOrm).where(
                TaskSubCompetencyNodeOrm.task_id == task.id
            )
        )
        await self._session.execute(
            delete(TaskCompetencyNodeOrm).where(
                TaskCompetencyNodeOrm.task_id == task.id
            )
        )
        await self._session.execute(
            delete(TaskCategoryNodeOrm).where(TaskCategoryNodeOrm.task_id == task.id)
        )

        for node_cat in task.category_nodes:
            self._session.add(
                TaskCategoryNodeOrm(
                    id=node_cat.id,
                    task_id=task.id,
                    category_id=node_cat.category_id,
                    position=node_cat.position,
                )
            )

        for node_comp in task.competency_nodes:
            self._session.add(
                TaskCompetencyNodeOrm(
                    id=node_comp.id,
                    task_id=task.id,
                    competency_id=node_comp.competency_id,
                    category_id=node_comp.category_id,
                    is_required=node_comp.is_required,
                    position=node_comp.position,
                )
            )

        for node_sub in task.sub_competency_nodes:
            self._session.add(
                TaskSubCompetencyNodeOrm(
                    id=node_sub.id,
                    task_id=task.id,
                    sub_competency_id=node_sub.sub_competency_id,
                    competency_id=node_sub.competency_id,
                    target_level=int(node_sub.target_level),
                    weight=node_sub.weight,
                    position=node_sub.position,
                )
            )

        await self._session.flush()

    async def _load_normalized_graph(
        self,
        task_id: UUID,
    ) -> tuple[
        list[TaskCategoryNode],
        list[TaskCompetencyNode],
        list[TaskSubCompetencyNode],
    ]:
        category_rows: Sequence[TaskCategoryNodeOrm] = (
            await self._session.scalars(
                select(TaskCategoryNodeOrm)
                .where(TaskCategoryNodeOrm.task_id == task_id)
                .order_by(TaskCategoryNodeOrm.position)
            )
        ).all()
        competency_rows: Sequence[TaskCompetencyNodeOrm] = (
            await self._session.scalars(
                select(TaskCompetencyNodeOrm)
                .where(TaskCompetencyNodeOrm.task_id == task_id)
                .order_by(TaskCompetencyNodeOrm.position)
            )
        ).all()
        sub_rows: Sequence[TaskSubCompetencyNodeOrm] = (
            await self._session.scalars(
                select(TaskSubCompetencyNodeOrm)
                .where(TaskSubCompetencyNodeOrm.task_id == task_id)
                .order_by(TaskSubCompetencyNodeOrm.position)
            )
        ).all()

        competency_ids = [row.competency_id for row in competency_rows]
        sub_ids = [row.sub_competency_id for row in sub_rows]
        category_ids = [row.category_id for row in category_rows]

        competency_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(CompetencyOrm).where(CompetencyOrm.id.in_(competency_ids))
                )
            ).all()
        }
        sub_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(SubCompetencyOrm).where(SubCompetencyOrm.id.in_(sub_ids))
                )
            ).all()
        }
        category_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(CategoryOrm).where(CategoryOrm.id.in_(category_ids))
                )
            ).all()
        }

        competencies: dict[UUID, Competency] = {}
        for row_comp in competency_rows:
            model = competency_models.get(row_comp.competency_id)
            if model is None:
                continue
            competencies[row_comp.competency_id] = Competency(
                id=model.id,
                category_id=row_comp.category_id,
                name=model.name,
                description=model.description,
                sub_competencies=[],
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

        categories: dict[UUID, Category] = {}
        for row_cat in category_rows:
            model_cat = category_models.get(row_cat.category_id)
            if model_cat is None:
                continue
            categories[row_cat.category_id] = Category(
                id=model_cat.id,
                name=model_cat.name,
                description=model_cat.description,
                emoji=model_cat.emoji,
                created_at=model_cat.created_at,
                updated_at=model_cat.updated_at,
            )

        category_nodes = [
            TaskCategoryNode(
                id=row.id,
                task_id=row.task_id,
                category_id=row.category_id,
                position=row.position,
                category=categories.get(row.category_id),
            )
            for row in category_rows
        ]
        competency_nodes = [
            TaskCompetencyNode(
                id=row.id,
                task_id=row.task_id,
                competency_id=row.competency_id,
                category_id=row.category_id,
                is_required=row.is_required,
                position=row.position,
                category=categories.get(row.category_id),
                competency=competencies.get(row.competency_id),
            )
            for row in competency_rows
        ]
        sub_nodes = [
            TaskSubCompetencyNode(
                id=row.id,
                task_id=row.task_id,
                sub_competency_id=row.sub_competency_id,
                competency_id=row.competency_id,
                target_level=CompetencyLevel(row.target_level),
                weight=row.weight,
                position=row.position,
                competency=competencies.get(row.competency_id),
                sub_competency=sub_models.get(row.sub_competency_id),
            )
            for row in sub_rows
        ]
        return category_nodes, competency_nodes, sub_nodes

    def to_domain(self, model: TaskOrm) -> Task:
        return task_from_orm(model)

    def to_model(self, entity: Task) -> TaskOrm:
        return task_to_orm(entity)


class _TestResultRepository(
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
            options.append(
                selectinload(TestResultOrm.llm_assessment).selectinload(
                    TestResultLLMAssessmentOrm.feedback_items
                )
            )
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
        await self._session.execute(
            delete(TestResultLLMFeedbackOrm).where(
                TestResultLLMFeedbackOrm.assessment_id.in_(
                    select(TestResultLLMAssessmentOrm.id).where(
                        TestResultLLMAssessmentOrm.test_result_id == entity.id
                    )
                )
            )
        )
        await self._session.execute(
            delete(TestResultLLMAssessmentOrm).where(
                TestResultLLMAssessmentOrm.test_result_id == entity.id
            )
        )

        for position, item in enumerate(entity.question_answers):
            self._session.add(
                TestResultQuestionAnswerOrm(
                    test_result_id=entity.id,
                    question=item.question,
                    answer=item.answer,
                    position=position,
                )
            )
        if entity.llm_assessment is not None:
            assessment_id = entity.llm_assessment.id
            self._session.add(
                TestResultLLMAssessmentOrm(
                    id=assessment_id,
                    test_result_id=entity.id,
                    passed=entity.llm_assessment.passed,
                    score=entity.llm_assessment.score,
                    feedback=entity.llm_assessment.feedback,
                    criteria_version=entity.llm_assessment.criteria_version,
                    raw_test_score=entity.llm_assessment.raw_test_score,
                    penalized_test_score=entity.llm_assessment.penalized_test_score,
                    attempt_penalty_applied=entity.llm_assessment.attempt_penalty_applied,
                    final_score=entity.llm_assessment.final_score,
                )
            )
            for position, item_f in enumerate(entity.llm_assessment.feedback_items):
                self._session.add(
                    TestResultLLMFeedbackOrm(
                        assessment_id=assessment_id,
                        type=item_f.type,
                        value=item_f.value,
                        position=position,
                    )
                )

        await self._session.flush()

    def to_domain(self, model: TestResultOrm) -> TestResult:
        return test_result_from_orm(model)

    def to_model(self, entity: TestResult) -> TestResultOrm:
        return test_result_to_orm(entity)
