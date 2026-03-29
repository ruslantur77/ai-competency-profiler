from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from competency_system.application.ports.repositories import Repository
from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    RefreshToken,
    SubCompetency,
    Task,
    TestResult,
    User,
    Vacancy,
    VacancyGraphSuggestion,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.infrastructure.persistence.mappers import (
    candidate_from_orm,
    candidate_to_orm,
    category_from_orm,
    category_to_orm,
    competency_from_orm,
    competency_to_orm,
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
)
from competency_system.infrastructure.persistence.models import (
    CandidateOrm,
    CategoryOrm,
    CompetencyOrm,
    RefreshTokenOrm,
    SubCompetencyOrm,
    TaskOrm,
    TestResultOrm,
    UserOrm,
    VacancyOrm,
    VacancyCategoryNodeOrm,
    VacancyCompetencyNodeOrm,
    VacancySubCompetencyNodeOrm,
    VacancySuggestionOrm,
)

DomainT = TypeVar("DomainT")
OrmT = TypeVar("OrmT")


class SQLAlchemyRepository(Generic[DomainT, OrmT], Repository[DomainT]):
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
        statement = select(self.model)
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

        category_position = 0
        competency_position = 0
        sub_position = 0
        for category in vacancy.categories:
            self._session.add(
                VacancyCategoryNodeOrm(
                    vacancy_id=vacancy.id,
                    category_id=category.id,
                    name=category.name,
                    description=category.description,
                    emoji=category.emoji,
                    position=category_position,
                )
            )
            category_position += 1

            for competency in category.competencies:
                self._session.add(
                    VacancyCompetencyNodeOrm(
                        vacancy_id=vacancy.id,
                        competency_id=competency.id,
                        category_id=category.id,
                        name=competency.name,
                        description=competency.description,
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
                            name=sub.name,
                            description=sub.description,
                            target_level=int(sub.target_level),
                            weight=sub.weight,
                            position=sub_position,
                        )
                    )
                    sub_position += 1
        await self._session.flush()

    async def _load_normalized_graph(
        self,
        vacancy_id: UUID,
    ) -> tuple[list[Category], list[Competency]] | None:
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

        subs_by_competency: dict[UUID, list[SubCompetency]] = {}
        for row in sub_rows:
            subs_by_competency.setdefault(row.competency_id, []).append(
                SubCompetency(
                    id=row.sub_competency_id,
                    name=row.name,
                    description=row.description,
                    target_level=CompetencyLevel(row.target_level),
                    weight=row.weight,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )

        competencies_by_category: dict[UUID, list[Competency]] = {}
        all_competencies: list[Competency] = []
        for row in competency_rows:
            competency = Competency(
                id=row.competency_id,
                category_id=row.category_id,
                name=row.name,
                description=row.description,
                is_required=row.is_required,
                sub_competencies=subs_by_competency.get(row.competency_id, []),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            competencies_by_category.setdefault(row.category_id, []).append(competency)
            all_competencies.append(competency)

        categories = [
            Category(
                id=row.category_id,
                name=row.name,
                description=row.description,
                emoji=row.emoji,
                competencies=competencies_by_category.get(row.category_id, []),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in category_rows
        ]
        return categories, all_competencies


class CandidateRepository(
    SQLAlchemyRepository[Candidate, CandidateOrm],
):
    model = CandidateOrm

    async def get_by_external_id(self, external_id: str) -> Candidate | None:
        statement = select(self.model).where(CandidateOrm.external_id == external_id)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: CandidateOrm) -> Candidate:
        return candidate_from_orm(model)

    def to_model(self, entity: Candidate) -> CandidateOrm:
        return candidate_to_orm(entity)


class TaskRepository(SQLAlchemyRepository[Task, TaskOrm]):
    model = TaskOrm

    async def get_by_external_id(self, external_id: str) -> Task | None:
        statement = select(self.model).where(TaskOrm.external_id == external_id)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return self.to_domain(model)

    def to_domain(self, model: TaskOrm) -> Task:
        return task_from_orm(model)

    def to_model(self, entity: Task) -> TaskOrm:
        return task_to_orm(entity)


class TestResultRepository(
    SQLAlchemyRepository[TestResult, TestResultOrm],
):
    model = TestResultOrm

    def to_domain(self, model: TestResultOrm) -> TestResult:
        return test_result_from_orm(model)

    def to_model(self, entity: TestResult) -> TestResultOrm:
        return test_result_to_orm(entity)


class VacancySuggestionRepository(
    SQLAlchemyRepository[VacancyGraphSuggestion, VacancySuggestionOrm],
):
    model = VacancySuggestionOrm

    async def list_by_vacancy(self, vacancy_id: UUID) -> Sequence[VacancyGraphSuggestion]:
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
