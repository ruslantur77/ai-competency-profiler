from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from competency_system.application.errors import ValidationError


def validate_status_transition[StatusT: StrEnum](
    *,
    current: StatusT,
    target: StatusT,
    allowed_transitions: Mapping[StatusT, set[StatusT]],
) -> None:
    if target == current:
        return
    allowed = allowed_transitions.get(current, set())
    if target not in allowed:
        raise ValidationError(
            "Invalid status transition: "
            f"{current.value} -> {target.value}"
        )


def validate_ready_graph_requirement[StatusT: StrEnum](
    *,
    current: StatusT,
    target: StatusT,
    ready_status: StatusT,
    has_sub_competency_nodes: bool,
    entity_name: str,
) -> None:
    if (
        current != ready_status
        and target == ready_status
        and not has_sub_competency_nodes
    ):
        raise ValidationError(
            f"{entity_name} graph must contain at least one sub-competency"
        )
