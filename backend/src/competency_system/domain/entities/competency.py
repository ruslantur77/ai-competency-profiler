from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from competency_system.domain.entities.base import Entity


@dataclass(kw_only=True)
class SubCompetency(Entity):
    """Sub-competency in the canonical ontology."""

    competency_id: UUID = UUID(int=0)
    name: str
    description: str = ""
    competency: Competency | None = None


@dataclass(kw_only=True)
class Competency(Entity):
    """Competency in the canonical ontology."""

    category_id: UUID
    name: str
    description: str = ""
    sub_competencies: list[SubCompetency] = field(default_factory=list)
    category: Category | None = None


@dataclass(kw_only=True)
class Category(Entity):
    """Competency category."""

    name: str
    description: str = ""
    emoji: str = "📋"
    competencies: list[Competency] = field(default_factory=list)
