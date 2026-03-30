from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from competency_system.application.ports.repositories import Repository
from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    RankingSnapshot,
    RefreshToken,
    SubCompetency,
    Task,
    TaskCompetencyMapping,
    TestResult,
    User,
    Vacancy,
    VacancyGraphSuggestion,
    WebhookEvent,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.infrastructure.persistence.mappers import (
    candidate_from_orm,
    candidate_to_orm,
    category_from_orm,
    category_to_orm,
    competency_from_orm,
    competency_to_orm,
    ranking_snapshot_from_orm,
    ranking_snapshot_to_orm,
    refresh_token_from_orm,
    refresh_token_to_orm,
    subcompetency_from_orm,
    subcompetency_to_orm,
    task_from_orm,
    task_to_orm,
    test_result_from_orm,
    test_result_to_orm,
    user_from_orm,
    user_to_orm,
    vacancy_from_orm,
    vacancy_suggestion_from_orm,
    vacancy_suggestion_to_orm,
    vacancy_to_orm,
    webhook_event_from_orm,
    webhook_event_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CandidateSubCompetencyAchievementOrm,
    CategoryOrm,
    CompetencyOrm,
    RankingSnapshotOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    TaskSubCompetencyMappingOrm,
    TestResultLLMAssessmentOrm,
    TestResultLLMIssueOrm,
    TestResultLLMStrengthOrm,
    TestResultOrm,
    TestResultQuestionAnswerOrm,
    UserOrm,
    VacancyCategoryNodeOrm,
    VacancyCompetencyNodeOrm,
    VacancyOrm,
    VacancySubCompetencyNodeOrm,
    VacancySuggestionOrm,
    WebhookEventOrm,
)

type CategoryGraph = tuple[list[Category], list[Competency]]


class SQLAlchemyRepository[DomainT, OrmT](Repository[DomainT]):
    model: type[OrmT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def load_options(self) -> Sequence[Any]:
        return ()

    def to_domain(self, model: OrmT) -> DomainT:
        raise NotImplementedError

    def to_model(self, entity: DomainT) -> OrmT:
        raise NotImplementedError

    async def get(self, entity_id: UUID) -> DomainT | None:
        model = await self._session.get(
            self.model,
            entity_id,
            options=list(self.load_options()),
        )
        if model is None:
            return None
        return self.to_domain(model)

    async def list(self) -> Sequence[DomainT]:
        statement = select(self.model).options(*self.load_options())
        result = await self._session.scalars(statement)
        return [self.to_domain(model) for model in result.all()]

    async def add(self, entity: DomainT) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()


class CategoryRepository(SQLAlchemyRepository[Category, CategoryOrm]):
    model = CategoryOrm

    def load_options(self) -> Sequence[Any]:
        return (
            selectinload(CategoryOrm.competencies).selectinload(
                CompetencyOrm.sub_competencies
            ),
        )

    def to_domain(self, model: CategoryOrm) -> Category:
        return category_from_orm(model)

    def to_model(self, entity: Category) -> CategoryOrm:
        return category_to_orm(entity)


class CompetencyRepository(
    SQLAlchemyRepository[Competency, CompetencyOrm],
):
    model = CompetencyOrm

    def load_options(self) -> Sequence[Any]:
        return (selectinload(CompetencyOrm.sub_competencies),)

    def to_domain(self, model: CompetencyOrm) -> Competency:
        return competency_from_orm(model)

    def to_model(self, entity: Competency) -> CompetencyOrm:
        return competency_to_orm(entity)


class SubCompetencyRepository(
    SQLAlchemyRepository[SubCompetency, SubCompetencyOrm],
):
    model = SubCompetencyOrm

    def to_domain(self, model: SubCompetencyOrm) -> SubCompetency:
        return subcompetency_from_orm(model)

    def to_model(self, entity: SubCompetency) -> SubCompetencyOrm:
        return subcompetency_to_orm(entity)


class VacancyRepository(SQLAlchemyRepository[Vacancy, VacancyOrm]):
    model = VacancyOrm

    async def get(self, entity_id: UUID) -> Vacancy | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        vacancy = self.to_domain(model)
        normalized = await self._load_normalized_graph(vacancy.id)
        if normalized is not None:
            vacancy.categories, vacancy.competencies = normalized
        return vacancy

    async def list(self) -> Sequence[Vacancy]:
        statement = select(self.model).order_by(VacancyOrm.created_at.desc())
        result = await self._session.scalars(statement)
        vacancies = [self.to_domain(model) for model in result.all()]
        for vacancy in vacancies:
            normalized = await self._load_normalized_graph(vacancy.id)
            if normalized is not None:
                vacancy.categories, vacancy.competencies = normalized
        return vacancies

    async def list_by_statuses(
        self, statuses: set[str] | None = None
    ) -> Sequence[Vacancy]:
        statement = select(self.model).order_by(VacancyOrm.created_at.desc())
        if statuses:
            statement = statement.where(VacancyOrm.status.in_(statuses))
        result = await self._session.scalars(statement)
        vacancies = [self.to_domain(model) for model in result.all()]
        for vacancy in vacancies:
            normalized = await self._load_normalized_graph(vacancy.id)
            if normalized is not None:
                vacancy.categories, vacancy.competencies = normalized
        return vacancies

    async def add(self, entity: Vacancy) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._upsert_canonical_graph(entity)
        await self._session.flush()
        await self._replace_normalized_graph(entity)

    def to_domain(self, model: VacancyOrm) -> Vacancy:
        return vacancy_from_orm(model)

    def to_model(self, entity: Vacancy) -> VacancyOrm:
        return vacancy_to_orm(entity)

    async def _replace_normalized_graph(self, vacancy: Vacancy) -> None:
        await self._session.execute(
            delete(VacancySubCompetencyNodeOrm).where(
                VacancySubCompetencyNodeOrm.vacancy_id == vacancy.id
            )
        )
        await self._session.execute(
            delete(VacancyCompetencyNodeOrm).where(
                VacancyCompetencyNodeOrm.vacancy_id == vacancy.id
            )
        )
        await self._session.execute(
            delete(VacancyCategoryNodeOrm).where(
                VacancyCategoryNodeOrm.vacancy_id == vacancy.id
            )
        )

        if vacancy.categories:
            category_order = [category.id for category in vacancy.categories]
            competencies_source = [
                competency
                for category in vacancy.categories
                for competency in category.competencies
            ]
        else:
            seen: set[UUID] = set()
            category_order = []
            competencies_source = list(vacancy.competencies)
            for competency in competencies_source:
                if competency.category_id not in seen:
                    seen.add(competency.category_id)
                    category_order.append(competency.category_id)

        for category_position, category_id in enumerate(category_order):
            self._session.add(
                VacancyCategoryNodeOrm(
                    vacancy_id=vacancy.id,
                    category_id=category_id,
                    position=category_position,
                )
            )

        competency_position = 0
        sub_position = 0
        for competency in competencies_source:
            self._session.add(
                VacancyCompetencyNodeOrm(
                    vacancy_id=vacancy.id,
                    competency_id=competency.id,
                    category_id=competency.category_id,
                    is_required=competency.is_required,
                    position=competency_position,
                )
            )
            competency_position += 1

            for sub in competency.sub_competencies:
                self._session.add(
                    VacancySubCompetencyNodeOrm(
                        vacancy_id=vacancy.id,
                        sub_competency_id=sub.id,
                        competency_id=competency.id,
                        target_level=int(sub.target_level),
                        weight=sub.weight,
                        position=sub_position,
                    )
                )
                sub_position += 1
        await self._session.flush()

    async def _upsert_canonical_graph(self, vacancy: Vacancy) -> None:
        categories_by_id: dict[UUID, Category] = {
            category.id: category for category in vacancy.categories
        }
        competencies_source: list[Competency]
        if vacancy.categories:
            competencies_source = [
                competency
                for category in vacancy.categories
                for competency in category.competencies
            ]
        else:
            competencies_source = list(vacancy.competencies)

        for competency in competencies_source:
            if competency.category_id not in categories_by_id:
                categories_by_id[competency.category_id] = Category(
                    id=competency.category_id,
                    name=f"Category {competency.category_id}",
                    description="",
                    emoji="📋",
                    competencies=[],
                )

        for category in categories_by_id.values():
            await self._session.merge(
                CategoryOrm(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    emoji=category.emoji,
                )
            )

        for competency in competencies_source:
            await self._session.merge(
                CompetencyOrm(
                    id=competency.id,
                    category_id=competency.category_id,
                    name=competency.name,
                    description=competency.description,
                )
            )
            for sub in competency.sub_competencies:
                await self._session.merge(
                    SubCompetencyOrm(
                        id=sub.id,
                        competency_id=competency.id,
                        name=sub.name,
                        description=sub.description,
                    )
                )

    async def _load_normalized_graph(
        self,
        vacancy_id: UUID,
    ) -> CategoryGraph | None:
        category_rows = (
            await self._session.scalars(
                select(VacancyCategoryNodeOrm)
                .where(VacancyCategoryNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancyCategoryNodeOrm.position)
            )
        ).all()
        if not category_rows:
            return None

        competency_rows = (
            await self._session.scalars(
                select(VacancyCompetencyNodeOrm)
                .where(VacancyCompetencyNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancyCompetencyNodeOrm.position)
            )
        ).all()
        sub_rows = (
            await self._session.scalars(
                select(VacancySubCompetencyNodeOrm)
                .where(VacancySubCompetencyNodeOrm.vacancy_id == vacancy_id)
                .order_by(VacancySubCompetencyNodeOrm.position)
            )
        ).all()

        category_ids = [row.category_id for row in category_rows]
        competency_ids = [row.competency_id for row in competency_rows]
        sub_ids = [row.sub_competency_id for row in sub_rows]

        category_models = {
            model.id: model
            for model in (
                await self._session.scalars(
                    select(CategoryOrm).where(CategoryOrm.id.in_(category_ids))
                )
            ).all()
        }
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

        subs_by_competency: dict[UUID, list[SubCompetency]] = {}
        for sub_row in sub_rows:
            sub_model = sub_models.get(sub_row.sub_competency_id)
            if sub_model is None:
                continue
            subs_by_competency.setdefault(sub_row.competency_id, []).append(
                SubCompetency(
                    id=sub_model.id,
                    name=sub_model.name,
                    description=sub_model.description,
                    target_level=CompetencyLevel(sub_row.target_level),
                    weight=sub_row.weight,
                    created_at=sub_model.created_at,
                    updated_at=sub_model.updated_at,
                )
            )

        competencies_by_category: dict[UUID, list[Competency]] = {}
        all_competencies: list[Competency] = []
        for competency_row in competency_rows:
            competency_model = competency_models.get(competency_row.competency_id)
            if competency_model is None:
                continue
            competency = Competency(
                id=competency_model.id,
                category_id=competency_row.category_id,
                name=competency_model.name,
                description=competency_model.description,
                is_required=competency_row.is_required,
                sub_competencies=subs_by_competency.get(
                    competency_row.competency_id, []
                ),
                created_at=competency_model.created_at,
                updated_at=competency_model.updated_at,
            )
            competencies_by_category.setdefault(competency_row.category_id, []).append(
                competency
            )
            all_competencies.append(competency)

        categories = []
        for category_row in category_rows:
            category_model = category_models.get(category_row.category_id)
            if category_model is None:
                continue
            categories.append(
                Category(
                    id=category_model.id,
                    name=category_model.name,
                    description=category_model.description,
                    emoji=category_model.emoji,
                    competencies=competencies_by_category.get(
                        category_row.category_id, []
                    ),
                    created_at=category_model.created_at,
                    updated_at=category_model.updated_at,
                )
            )

        return categories, all_competencies


class CandidateRepository(
    SQLAlchemyRepository[Candidate, CandidateOrm],
):
    model = CandidateOrm

    async def get(self, entity_id: UUID) -> Candidate | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        candidate = self.to_domain(model)
        candidate.achieved_subcompetency_ids = await self._get_achievements(model.id)
        return candidate

    async def get_by_external_id(self, external_id: str) -> Candidate | None:
        statement = select(self.model).where(CandidateOrm.external_id == external_id)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        candidate = self.to_domain(model)
        candidate.achieved_subcompetency_ids = await self._get_achievements(model.id)
        return candidate

    async def list_by_vacancy(self, vacancy_id: UUID) -> Sequence[Candidate]:
        statement = (
            select(CandidateOrm)
            .where(CandidateOrm.vacancy_id == vacancy_id)
            .order_by(CandidateOrm.created_at.asc())
        )
        result = await self._session.scalars(statement)
        rows = result.all()
        achievements_by_candidate = await self._get_achievements_batch(
            [row.id for row in rows]
        )
        candidates: list[Candidate] = []
        for row in rows:
            candidate = self.to_domain(row)
            candidate.achieved_subcompetency_ids = achievements_by_candidate.get(
                row.id, set()
            )
            candidates.append(candidate)
        return candidates

    async def add(self, entity: Candidate) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

        await self._session.execute(
            delete(CandidateSubCompetencyAchievementOrm).where(
                CandidateSubCompetencyAchievementOrm.candidate_id == entity.id
            )
        )
        for sub_id in sorted(entity.achieved_subcompetency_ids, key=str):
            self._session.add(
                CandidateSubCompetencyAchievementOrm(
                    candidate_id=entity.id,
                    sub_competency_id=sub_id,
                )
            )
        await self._session.flush()

    def to_domain(self, model: CandidateOrm) -> Candidate:
        return candidate_from_orm(model)

    def to_model(self, entity: Candidate) -> CandidateOrm:
        return candidate_to_orm(entity)

    async def _get_achievements(self, candidate_id: UUID) -> set[UUID]:
        rows = (
            await self._session.scalars(
                select(CandidateSubCompetencyAchievementOrm.sub_competency_id).where(
                    CandidateSubCompetencyAchievementOrm.candidate_id == candidate_id
                )
            )
        ).all()
        return set(rows)

    async def _get_achievements_batch(
        self, candidate_ids: list[UUID]
    ) -> dict[UUID, set[UUID]]:
        if not candidate_ids:
            return {}
        rows = (
            await self._session.execute(
                select(
                    CandidateSubCompetencyAchievementOrm.candidate_id,
                    CandidateSubCompetencyAchievementOrm.sub_competency_id,
                ).where(
                    CandidateSubCompetencyAchievementOrm.candidate_id.in_(candidate_ids)
                )
            )
        ).all()
        result: dict[UUID, set[UUID]] = {
            candidate_id: set() for candidate_id in candidate_ids
        }
        for candidate_id, sub_competency_id in rows:
            result.setdefault(candidate_id, set()).add(sub_competency_id)
        return result


class TaskRepository(SQLAlchemyRepository[Task, TaskOrm]):
    model = TaskOrm

    async def get(self, entity_id: UUID) -> Task | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        task = self.to_domain(model)
        task.competency_mappings = await self._get_mappings(model.id)
        return task

    async def list(self) -> Sequence[Task]:
        result = await self._session.scalars(select(self.model))
        rows = result.all()
        mappings_by_task = await self._get_mappings_batch([row.id for row in rows])
        tasks: list[Task] = []
        for row in rows:
            task = self.to_domain(row)
            task.competency_mappings = mappings_by_task.get(row.id, [])
            tasks.append(task)
        return tasks

    async def get_by_external_id(self, external_id: str) -> Task | None:
        statement = select(self.model).where(TaskOrm.external_id == external_id)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        task = self.to_domain(model)
        task.competency_mappings = await self._get_mappings(model.id)
        return task

    async def add(self, entity: Task) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

        await self._session.execute(
            delete(TaskSubCompetencyMappingOrm).where(
                TaskSubCompetencyMappingOrm.task_id == entity.id
            )
        )
        for position, mapping in enumerate(entity.competency_mappings):
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

    async def _get_mappings(self, task_id: UUID) -> list[TaskCompetencyMapping]:
        rows = (
            await self._session.scalars(
                select(TaskSubCompetencyMappingOrm)
                .where(TaskSubCompetencyMappingOrm.task_id == task_id)
                .order_by(TaskSubCompetencyMappingOrm.position)
            )
        ).all()
        return [
            TaskCompetencyMapping(
                sub_competency_id=row.sub_competency_id,
                weight=row.weight,
            )
            for row in rows
        ]

    async def _get_mappings_batch(
        self, task_ids: list[UUID]
    ) -> dict[UUID, list[TaskCompetencyMapping]]:
        if not task_ids:
            return {}
        rows = (
            await self._session.scalars(
                select(TaskSubCompetencyMappingOrm)
                .where(TaskSubCompetencyMappingOrm.task_id.in_(task_ids))
                .order_by(
                    TaskSubCompetencyMappingOrm.task_id,
                    TaskSubCompetencyMappingOrm.position,
                )
            )
        ).all()
        result: dict[UUID, list[TaskCompetencyMapping]] = {
            task_id: [] for task_id in task_ids
        }
        for row in rows:
            result.setdefault(row.task_id, []).append(
                TaskCompetencyMapping(
                    sub_competency_id=row.sub_competency_id,
                    weight=row.weight,
                )
            )
        return result


class TestResultRepository(
    SQLAlchemyRepository[TestResult, TestResultOrm],
):
    model = TestResultOrm

    async def get(self, entity_id: UUID) -> TestResult | None:
        model = await self._session.get(self.model, entity_id)
        if model is None:
            return None
        return await self._hydrate_result(model)

    async def list(self) -> Sequence[TestResult]:
        result = await self._session.scalars(select(self.model))
        rows = result.all()
        return [await self._hydrate_result(row) for row in rows]

    async def add(self, entity: TestResult) -> None:
        model = self.to_model(entity)
        await self._session.merge(model)
        await self._session.flush()

        await self._session.execute(
            delete(TestResultQuestionAnswerOrm).where(
                TestResultQuestionAnswerOrm.test_result_id == entity.id
            )
        )
        for position, qa in enumerate(entity.question_answers):
            self._session.add(
                TestResultQuestionAnswerOrm(
                    test_result_id=entity.id,
                    question=str(qa.get("question", "")),
                    answer=str(qa.get("answer", "")),
                    position=position,
                )
            )

        existing_assessment = await self._session.scalar(
            select(TestResultLLMAssessmentOrm).where(
                TestResultLLMAssessmentOrm.test_result_id == entity.id
            )
        )
        if existing_assessment is not None:
            await self._session.execute(
                delete(TestResultLLMStrengthOrm).where(
                    TestResultLLMStrengthOrm.assessment_id == existing_assessment.id
                )
            )
            await self._session.execute(
                delete(TestResultLLMIssueOrm).where(
                    TestResultLLMIssueOrm.assessment_id == existing_assessment.id
                )
            )
            await self._session.delete(existing_assessment)
            await self._session.flush()

        if entity.llm_assessment is not None:
            llm = entity.llm_assessment
            assessment = TestResultLLMAssessmentOrm(
                test_result_id=entity.id,
                passed=bool(llm.get("passed", entity.passed)),
                score=float(llm.get("score", entity.score)),
                feedback=str(llm.get("feedback", "")),
                criteria_version=str(llm.get("criteria_version", "")),
                raw_test_score=float(llm.get("raw_test_score", 0.0)),
                penalized_test_score=float(llm.get("penalized_test_score", 0.0)),
                attempt_penalty_applied=bool(llm.get("attempt_penalty_applied", False)),
                final_score=float(llm.get("final_score", entity.score)),
            )
            self._session.add(assessment)
            await self._session.flush()

            strengths = llm.get("strengths", [])
            if isinstance(strengths, list):
                for position, value in enumerate(strengths):
                    self._session.add(
                        TestResultLLMStrengthOrm(
                            assessment_id=assessment.id,
                            value=str(value),
                            position=position,
                        )
                    )

            issues = llm.get("issues", [])
            if isinstance(issues, list):
                for position, value in enumerate(issues):
                    self._session.add(
                        TestResultLLMIssueOrm(
                            assessment_id=assessment.id,
                            value=str(value),
                            position=position,
                        )
                    )

        await self._session.flush()

    def to_domain(self, model: TestResultOrm) -> TestResult:
        return test_result_from_orm(model)

    def to_model(self, entity: TestResult) -> TestResultOrm:
        return test_result_to_orm(entity)

    async def _hydrate_result(self, model: TestResultOrm) -> TestResult:
        entity = self.to_domain(model)
        answers = (
            await self._session.scalars(
                select(TestResultQuestionAnswerOrm)
                .where(TestResultQuestionAnswerOrm.test_result_id == model.id)
                .order_by(TestResultQuestionAnswerOrm.position)
            )
        ).all()
        entity.question_answers = [
            {"question": row.question, "answer": row.answer} for row in answers
        ]

        assessment = await self._session.scalar(
            select(TestResultLLMAssessmentOrm).where(
                TestResultLLMAssessmentOrm.test_result_id == model.id
            )
        )
        if assessment is not None:
            strengths = (
                await self._session.scalars(
                    select(TestResultLLMStrengthOrm)
                    .where(TestResultLLMStrengthOrm.assessment_id == assessment.id)
                    .order_by(TestResultLLMStrengthOrm.position)
                )
            ).all()
            issues = (
                await self._session.scalars(
                    select(TestResultLLMIssueOrm)
                    .where(TestResultLLMIssueOrm.assessment_id == assessment.id)
                    .order_by(TestResultLLMIssueOrm.position)
                )
            ).all()
            entity.llm_assessment = {
                "passed": assessment.passed,
                "score": assessment.score,
                "feedback": assessment.feedback,
                "criteria_version": assessment.criteria_version,
                "raw_test_score": assessment.raw_test_score,
                "penalized_test_score": assessment.penalized_test_score,
                "attempt_penalty_applied": assessment.attempt_penalty_applied,
                "final_score": assessment.final_score,
                "strengths": [row.value for row in strengths],
                "issues": [row.value for row in issues],
            }
        else:
            entity.llm_assessment = None

        return entity


class VacancySuggestionRepository(
    SQLAlchemyRepository[VacancyGraphSuggestion, VacancySuggestionOrm],
):
    model = VacancySuggestionOrm

    async def list_by_vacancy(
        self, vacancy_id: UUID
    ) -> Sequence[VacancyGraphSuggestion]:
        statement = (
            select(self.model)
            .where(VacancySuggestionOrm.vacancy_id == vacancy_id)
            .order_by(VacancySuggestionOrm.created_at)
        )
        result = await self._session.scalars(statement)
        return [self.to_domain(model) for model in result.all()]

    def to_domain(self, model: VacancySuggestionOrm) -> VacancyGraphSuggestion:
        return vacancy_suggestion_from_orm(model)

    def to_model(self, entity: VacancyGraphSuggestion) -> VacancySuggestionOrm:
        return vacancy_suggestion_to_orm(entity)


class UserRepository(SQLAlchemyRepository[User, UserOrm]):
    model = UserOrm

    async def get_by_email(self, email: str) -> User | None:
        statement = select(UserOrm).where(UserOrm.email == email)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: UserOrm) -> User:
        return user_from_orm(model)

    def to_model(self, entity: User) -> UserOrm:
        return user_to_orm(entity)


class RefreshTokenRepository(SQLAlchemyRepository[RefreshToken, RefreshTokenOrm]):
    model = RefreshTokenOrm

    async def add_token(
        self,
        *,
        jti: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        token = RefreshTokenOrm(
            jti=jti,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self._session.merge(token)
        await self._session.flush()

    async def get_by_jti(self, jti: UUID) -> RefreshToken | None:
        statement = select(RefreshTokenOrm).where(RefreshTokenOrm.jti == jti)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        token = self.to_domain(model)
        if token.expires_at <= datetime.now(UTC):
            await self.revoke(token.jti)
            return None
        return token

    async def revoke(self, jti: UUID) -> None:
        statement = (
            update(RefreshTokenOrm)
            .where(RefreshTokenOrm.jti == jti)
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.execute(statement)
        await self._session.flush()

    def to_domain(self, model: RefreshTokenOrm) -> RefreshToken:
        return refresh_token_from_orm(model)

    def to_model(self, entity: RefreshToken) -> RefreshTokenOrm:
        return refresh_token_to_orm(entity)


class WebhookEventRepository(SQLAlchemyRepository[WebhookEvent, WebhookEventOrm]):
    model = WebhookEventOrm

    async def get_by_event_id(self, event_id: str) -> WebhookEvent | None:
        statement = select(WebhookEventOrm).where(WebhookEventOrm.event_id == event_id)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: WebhookEventOrm) -> WebhookEvent:
        return webhook_event_from_orm(model)

    def to_model(self, entity: WebhookEvent) -> WebhookEventOrm:
        return webhook_event_to_orm(entity)


class RankingSnapshotRepository(
    SQLAlchemyRepository[RankingSnapshot, RankingSnapshotOrm]
):
    model = RankingSnapshotOrm

    async def get_by_vacancy(self, vacancy_id: UUID) -> RankingSnapshot | None:
        statement = select(RankingSnapshotOrm).where(
            RankingSnapshotOrm.vacancy_id == vacancy_id
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: RankingSnapshotOrm) -> RankingSnapshot:
        return ranking_snapshot_from_orm(model)

    def to_model(self, entity: RankingSnapshot) -> RankingSnapshotOrm:
        return ranking_snapshot_to_orm(entity)
