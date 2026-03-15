"""Tests for the dynamics initializer service."""

import pytest

from app.dynamics import DynamicsGraph, EdgeType, NodeType
from app.services.dynamics_initializer import (
    DynamicsInitializer,
    _classify_edge_type,
    _classify_node_type,
)


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


class TestClassifyNodeType:
    def test_person_is_agent(self):
        assert _classify_node_type(["Person"]) == NodeType.AGENT

    def test_student_is_agent(self):
        assert _classify_node_type(["Student"]) == NodeType.AGENT

    def test_university_is_institution(self):
        assert _classify_node_type(["University"]) == NodeType.INSTITUTION

    def test_company_is_institution(self):
        assert _classify_node_type(["Company"]) == NodeType.INSTITUTION

    def test_unknown_label_defaults_to_agent(self):
        assert _classify_node_type(["AlienSpecies"]) == NodeType.AGENT

    def test_empty_labels_defaults_to_agent(self):
        assert _classify_node_type([]) == NodeType.AGENT

    def test_case_insensitive(self):
        assert _classify_node_type(["PROFESSOR"]) == NodeType.AGENT

    def test_first_matching_label_wins(self):
        # "Entity" is not in the map; "MediaOutlet" is INSTITUTION
        assert _classify_node_type(["Entity", "MediaOutlet"]) == NodeType.INSTITUTION


class TestClassifyEdgeType:
    def test_supports_is_influence(self):
        assert _classify_edge_type("SUPPORTS", "") == EdgeType.INFLUENCE

    def test_reports_on_is_information(self):
        assert _classify_edge_type("REPORTS_ON", "") == EdgeType.INFORMATION

    def test_works_for_is_membership(self):
        assert _classify_edge_type("WORKS_FOR", "") == EdgeType.MEMBERSHIP

    def test_competes_with_is_conflict(self):
        assert _classify_edge_type("COMPETES_WITH", "") == EdgeType.CONFLICT

    def test_funds_is_resource_flow(self):
        assert _classify_edge_type("FUNDS", "") == EdgeType.RESOURCE_FLOW

    def test_collaborates_is_cooperation(self):
        assert _classify_edge_type("COLLABORATES_WITH", "") == EdgeType.COOPERATION

    def test_unknown_defaults_to_influence(self):
        assert _classify_edge_type("SOMETHING_WEIRD", "") == EdgeType.INFLUENCE

    def test_fallback_to_edge_name(self):
        assert _classify_edge_type("", "supports") == EdgeType.INFLUENCE


# ---------------------------------------------------------------------------
# Full initializer
# ---------------------------------------------------------------------------

SAMPLE_GRAPH_DATA = {
    "graph_id": "test_graph",
    "nodes": [
        {
            "uuid": "uuid-alice",
            "name": "Alice",
            "labels": ["Entity", "Student"],
            "summary": "A student",
            "attributes": {},
        },
        {
            "uuid": "uuid-bob",
            "name": "Bob",
            "labels": ["Entity", "Professor"],
            "summary": "A professor",
            "attributes": {},
        },
        {
            "uuid": "uuid-mit",
            "name": "MIT",
            "labels": ["Entity", "University"],
            "summary": "A university",
            "attributes": {},
        },
    ],
    "edges": [
        {
            "uuid": "edge-1",
            "name": "studies_at",
            "fact": "Alice studies at MIT",
            "fact_type": "STUDIES_AT",
            "source_node_uuid": "uuid-alice",
            "target_node_uuid": "uuid-mit",
            "attributes": {},
        },
        {
            "uuid": "edge-2",
            "name": "works_for",
            "fact": "Bob works for MIT",
            "fact_type": "WORKS_FOR",
            "source_node_uuid": "uuid-bob",
            "target_node_uuid": "uuid-mit",
            "attributes": {},
        },
        {
            "uuid": "edge-3",
            "name": "mentors",
            "fact": "Bob mentors Alice",
            "fact_type": "MENTORS",
            "source_node_uuid": "uuid-bob",
            "target_node_uuid": "uuid-alice",
            "attributes": {},
        },
    ],
    "node_count": 3,
    "edge_count": 3,
}


class TestDynamicsInitializer:
    @pytest.fixture
    def init(self):
        return DynamicsInitializer()

    def test_creates_all_nodes(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        assert len(list(g._nodes)) == 3

    def test_node_types_correct(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        agents = g.nodes_by_type(NodeType.AGENT)
        institutions = g.nodes_by_type(NodeType.INSTITUTION)
        assert len(agents) == 2   # Alice, Bob
        assert len(institutions) == 1  # MIT

    def test_creates_all_edges(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        assert len(list(g._edges)) == 3

    def test_edge_types_correct(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        membership_edges = g.edges_by_type(EdgeType.MEMBERSHIP)
        influence_edges = g.edges_by_type(EdgeType.INFLUENCE)
        assert len(membership_edges) == 2  # studies_at, works_for
        assert len(influence_edges) == 1   # mentors

    def test_institution_id_assigned(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        # MIT should have institution_id = its own node_id
        institutions = g.nodes_by_type(NodeType.INSTITUTION)
        mit = institutions[0]
        assert mit.institution_id == mit.node_id

    def test_membership_assigns_institution(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        # Alice and Bob should have institution_id = MIT's node_id
        agents = g.nodes_by_type(NodeType.AGENT)
        institutions = g.nodes_by_type(NodeType.INSTITUTION)
        mit_id = institutions[0].node_id
        for agent in agents:
            assert agent.institution_id == mit_id

    def test_source_entity_id_preserved(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        for node in g._nodes.values():
            assert node.source_entity_id is not None

    def test_initial_state_varies_by_type(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        agent = g.nodes_by_type(NodeType.AGENT)[0]
        inst = g.nodes_by_type(NodeType.INSTITUTION)[0]
        # Institutions should have higher resources than agents
        assert inst.state.resources > agent.state.resources

    def test_skips_dangling_edges(self, init):
        data = {
            "nodes": [{"uuid": "u1", "name": "A", "labels": ["Person"]}],
            "edges": [{
                "uuid": "e1", "name": "x", "fact": "", "fact_type": "SUPPORTS",
                "source_node_uuid": "u1", "target_node_uuid": "missing",
            }],
        }
        g = init.initialize(data)
        assert len(list(g._edges)) == 0

    def test_deterministic_ids(self, init):
        g1 = init.initialize(SAMPLE_GRAPH_DATA)
        g2 = init.initialize(SAMPLE_GRAPH_DATA)
        ids1 = sorted(g1._nodes.keys())
        ids2 = sorted(g2._nodes.keys())
        assert ids1 == ids2


class TestSuggestTemplates:
    @pytest.fixture
    def init(self):
        return DynamicsInitializer()

    def test_always_suggests_diffusion(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        suggestions = init.suggest_templates(g)
        assert "diffusion" in suggestions

    def test_suggests_opinion_for_agents(self, init):
        g = init.initialize(SAMPLE_GRAPH_DATA)
        suggestions = init.suggest_templates(g)
        assert "opinion" in suggestions

    def test_suggests_resource_for_resource_edges(self, init):
        data = {
            "nodes": [
                {"uuid": "u1", "name": "A", "labels": ["Company"]},
                {"uuid": "u2", "name": "B", "labels": ["Company"]},
            ],
            "edges": [{
                "uuid": "e1", "name": "funds", "fact": "", "fact_type": "FUNDS",
                "source_node_uuid": "u1", "target_node_uuid": "u2",
            }],
        }
        g = init.initialize(data)
        suggestions = init.suggest_templates(g)
        assert "resource" in suggestions
