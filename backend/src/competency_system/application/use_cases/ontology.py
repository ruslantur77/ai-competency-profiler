from __future__ import annotations

from uuid import UUID, uuid4

from competency_system.application.dtos.competency import (
    CategoryCreateDTO,
    CategoryDTO,
    CategoryUpdateDTO,
    CompetencyCreateDTO,
    CompetencyDTO,
    CompetencyUpdateDTO,
    SubCompetencyCreateDTO,
    SubCompetencyDTO,
    SubCompetencyUpdateDTO,
)
from competency_system.application.errors import ConflictError, NotFoundError
from competency_system.application.ports.repositories import (
    CandidateInclude,
    CategoryInclude,
    CompetencyInclude,
    TaskInclude,
    VacancyInclude,
)
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.entities import Category, Competency, SubCompetency


def _sub_competency_to_dto(entity: SubCompetency) -> SubCompetencyDTO:
    return SubCompetencyDTO(
        id=entity.id,
        competency_id=entity.competency_id,
        name=entity.name,
        description=entity.description,
        weight=entity.weight,
        target_level=entity.target_level,
    )


def _competency_to_dto(entity: Competency) -> CompetencyDTO:
    return CompetencyDTO(
        id=entity.id,
        category_id=entity.category_id,
        name=entity.name,
        description=entity.description,
        sub_competencies=[
            _sub_competency_to_dto(sub) for sub in entity.sub_competencies
        ],
    )


def _category_to_dto(entity: Category) -> CategoryDTO:
    return CategoryDTO(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        emoji=entity.emoji,
        competencies=[_competency_to_dto(comp) for comp in entity.competencies],
    )


class ListCategoriesUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[CategoryDTO]:
        async with self._uow as uow:
            categories = await uow.categories.get_list(
                include={CategoryInclude.SUB_COMPETENCIES}
            )
            return [_category_to_dto(item) for item in categories]


class GetCategoryUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, category_id: UUID) -> CategoryDTO:
        async with self._uow as uow:
            category = await uow.categories.get(
                category_id, include={CategoryInclude.SUB_COMPETENCIES}
            )
            if category is None:
                raise NotFoundError(f"Category {category_id} not found")
            return _category_to_dto(category)


class CreateCategoryUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CategoryCreateDTO) -> CategoryDTO:
        async with self._uow as uow:
            category = Category(
                id=uuid4(),
                name=command.name,
                description=command.description,
                emoji=command.emoji,
            )
            await uow.categories.add(category)
            await uow.commit()
            return _category_to_dto(category)


class UpdateCategoryUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, category_id: UUID, command: CategoryUpdateDTO
    ) -> CategoryDTO:
        async with self._uow as uow:
            category = await uow.categories.get(
                category_id, include={CategoryInclude.SUB_COMPETENCIES}
            )
            if category is None:
                raise NotFoundError(f"Category {category_id} not found")

            if command.name is not None:
                category.name = command.name
            if command.description is not None:
                category.description = command.description
            if command.emoji is not None:
                category.emoji = command.emoji

            await uow.categories.add(category)
            await uow.commit()
            return _category_to_dto(category)


class ListCompetenciesUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[CompetencyDTO]:
        async with self._uow as uow:
            competencies = await uow.competencies.get_list(
                include={CompetencyInclude.SUB_COMPETENCIES}
            )
            return [_competency_to_dto(item) for item in competencies]


class GetCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, competency_id: UUID) -> CompetencyDTO:
        async with self._uow as uow:
            competency = await uow.competencies.get(
                competency_id, include={CompetencyInclude.SUB_COMPETENCIES}
            )
            if competency is None:
                raise NotFoundError(f"Competency {competency_id} not found")
            return _competency_to_dto(competency)


class CreateCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CompetencyCreateDTO) -> CompetencyDTO:
        async with self._uow as uow:
            category = await uow.categories.get(command.category_id)
            if category is None:
                raise NotFoundError(f"Category {command.category_id} not found")

            competency = Competency(
                id=uuid4(),
                category_id=command.category_id,
                name=command.name,
                description=command.description,
            )
            await uow.competencies.add(competency)
            await uow.commit()
            return _competency_to_dto(competency)


class UpdateCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        competency_id: UUID,
        command: CompetencyUpdateDTO,
    ) -> CompetencyDTO:
        async with self._uow as uow:
            competency = await uow.competencies.get(
                competency_id,
                include={CompetencyInclude.SUB_COMPETENCIES},
            )
            if competency is None:
                raise NotFoundError(f"Competency {competency_id} not found")

            if command.category_id is not None:
                category = await uow.categories.get(command.category_id)
                if category is None:
                    raise NotFoundError(f"Category {command.category_id} not found")
                competency.category_id = command.category_id
            if command.name is not None:
                competency.name = command.name
            if command.description is not None:
                competency.description = command.description

            await uow.competencies.add(competency)
            await uow.commit()
            return _competency_to_dto(competency)


class ListSubCompetenciesUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[SubCompetencyDTO]:
        async with self._uow as uow:
            sub_competencies = await uow.sub_competencies.get_list()
            return [_sub_competency_to_dto(item) for item in sub_competencies]


class GetSubCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, sub_competency_id: UUID) -> SubCompetencyDTO:
        async with self._uow as uow:
            sub_competency = await uow.sub_competencies.get(sub_competency_id)
            if sub_competency is None:
                raise NotFoundError(f"Sub-competency {sub_competency_id} not found")
            return _sub_competency_to_dto(sub_competency)


class CreateSubCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SubCompetencyCreateDTO) -> SubCompetencyDTO:
        async with self._uow as uow:
            competency = await uow.competencies.get(command.competency_id)
            if competency is None:
                raise NotFoundError(f"Competency {command.competency_id} not found")

            sub_competency = SubCompetency(
                id=uuid4(),
                competency_id=command.competency_id,
                name=command.name,
                description=command.description,
                weight=command.weight,
                target_level=command.target_level,
            )
            await uow.sub_competencies.add(sub_competency)
            await uow.commit()
            return _sub_competency_to_dto(sub_competency)


class UpdateSubCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        sub_competency_id: UUID,
        command: SubCompetencyUpdateDTO,
    ) -> SubCompetencyDTO:
        async with self._uow as uow:
            sub_competency = await uow.sub_competencies.get(sub_competency_id)
            if sub_competency is None:
                raise NotFoundError(f"Sub-competency {sub_competency_id} not found")

            if command.competency_id is not None:
                competency = await uow.competencies.get(command.competency_id)
                if competency is None:
                    raise NotFoundError(f"Competency {command.competency_id} not found")
                sub_competency.competency_id = command.competency_id
            if command.name is not None:
                sub_competency.name = command.name
            if command.description is not None:
                sub_competency.description = command.description
            if command.weight is not None:
                sub_competency.weight = command.weight
            if command.target_level is not None:
                sub_competency.target_level = command.target_level

            await uow.sub_competencies.add(sub_competency)
            await uow.commit()
            return _sub_competency_to_dto(sub_competency)


class DeleteCategoryUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, category_id: UUID) -> None:
        async with self._uow as uow:
            category = await uow.categories.get(
                category_id, include={CategoryInclude.COMPETENCIES}
            )
            if category is None:
                raise NotFoundError(f"Category {category_id} not found")
            if category.competencies:
                raise ConflictError(
                    f"Cannot delete category {category_id}: dependent competencies exist"  # noqa: E501
                )
            await uow.categories.delete(category_id)
            await uow.commit()


class DeleteCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, competency_id: UUID) -> None:
        async with self._uow as uow:
            competency = await uow.competencies.get(
                competency_id, include={CompetencyInclude.SUB_COMPETENCIES}
            )
            if competency is None:
                raise NotFoundError(f"Competency {competency_id} not found")
            if competency.sub_competencies:
                raise ConflictError(
                    f"Cannot delete competency {competency_id}: dependent sub-competencies exist"  # noqa: E501
                )
            vacancies = await uow.vacancies.get_list(
                include={VacancyInclude.NORMALIZED_GRAPH}
            )
            if any(
                node.competency_id == competency_id
                for vacancy in vacancies
                for node in vacancy.competency_nodes
            ):
                raise ConflictError(
                    f"Cannot delete competency {competency_id}: used in vacancy graph"
                )
            await uow.competencies.delete(competency_id)
            await uow.commit()


class DeleteSubCompetencyUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, sub_competency_id: UUID) -> None:
        async with self._uow as uow:
            sub_competency = await uow.sub_competencies.get(sub_competency_id)
            if sub_competency is None:
                raise NotFoundError(f"Sub-competency {sub_competency_id} not found")

            tasks = await uow.tasks.get_list(include={TaskInclude.NORMALIZED_GRAPH})
            if any(
                node.sub_competency_id == sub_competency_id
                for task in tasks
                for node in task.sub_competency_nodes
            ):
                raise ConflictError(
                    f"Cannot delete sub-competency {sub_competency_id}: used in task graph"  # noqa: E501
                )

            candidates = await uow.candidates.get_list(
                include={CandidateInclude.ACHIEVEMENTS}
            )
            if any(
                achievement.sub_competency_id == sub_competency_id
                for candidate in candidates
                for achievement in candidate.achievements
            ):
                raise ConflictError(
                    f"Cannot delete sub-competency {sub_competency_id}: used in candidate achievements"  # noqa: E501
                )

            vacancies = await uow.vacancies.get_list(
                include={VacancyInclude.NORMALIZED_GRAPH}
            )
            if any(
                node.sub_competency_id == sub_competency_id
                for vacancy in vacancies
                for node in vacancy.sub_competency_nodes
            ):
                raise ConflictError(
                    f"Cannot delete sub-competency {sub_competency_id}: used in vacancy graph"  # noqa: E501
                )

            await uow.sub_competencies.delete(sub_competency_id)
            await uow.commit()
