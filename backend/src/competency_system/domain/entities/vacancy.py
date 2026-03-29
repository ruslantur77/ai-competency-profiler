from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from competency_system.domain.entities.base import Entity
from competency_system.domain.value_objects.enums import VacancyStatus

if TYPE_CHECKING:
    from competency_system.domain.entities.competency import Category, Competency


@dataclass(kw_only=True)
class Vacancy(Entity):
    """Вакансия с графом компетенций.

    Упрощенная версия без events и сложной логики.
    """

    name: str
    description: str
    status: VacancyStatus = VacancyStatus.DRAFT

    # Опциональные поля
    experience: str = ""
    key_skills: list[str] = field(default_factory=list)

    # Граф компетенций
    categories: list[Category] = field(default_factory=list)
    competencies: list[Competency] = field(default_factory=list)

    # Метаданные
    error_message: str | None = None

    @property
    def is_ready(self) -> bool:
        """Проверка готовности графа."""
        return self.status == VacancyStatus.READY

    def get_required_competencies(self) -> list[Competency]:
        """Получить обязательные компетенции."""
        return [c for c in self.competencies if c.is_required]
