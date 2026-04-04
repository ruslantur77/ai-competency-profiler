from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.use_cases.vacancy import (
    _build_nodes_from_competencies,
    _map_category_node,
    _map_competency_node,
    _map_sub_competency_node,
)
from tests.fixtures.domain_graph import build_taxonomy

pytestmark = pytest.mark.unit


def test_vacancy_graph_node_builder_functions_map_fields() -> None:
    vacancy_id = uuid4()
    category, competency, sub1, _ = build_taxonomy()

    category_node = _map_category_node(vacancy_id, category.id, 0)
    competency_node = _map_competency_node(vacancy_id, competency, 1)
    sub_node = _map_sub_competency_node(vacancy_id, competency, sub1, 2)

    assert category_node.vacancy_id == vacancy_id
    assert competency_node.competency_id == competency.id
    assert competency_node.category_id == competency.category_id
    assert sub_node.sub_competency_id == sub1.id
    assert sub_node.position == 2


def test_build_nodes_from_competencies_preserves_category_order_and_positions() -> None:
    vacancy_id = uuid4()
    cat_a, comp_a, sub_a1, sub_a2 = build_taxonomy()
    cat_b, comp_b, sub_b1, _ = build_taxonomy()
    comp_b.category_id = cat_b.id
    comp_b.sub_competencies = [sub_b1]

    category_nodes, competency_nodes, sub_nodes = _build_nodes_from_competencies(
        vacancy_id, [comp_a, comp_b]
    )

    assert [node.category_id for node in category_nodes] == [cat_a.id, cat_b.id]
    assert [node.position for node in competency_nodes] == [0, 0]
    assert [node.position for node in sub_nodes] == [0, 1, 0]
