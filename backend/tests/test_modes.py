"""Tests for simulation modes framework."""

import json

import pytest

from app import create_app
from app.dynamics import (
    DynamicsGraph,
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeState,
    NodeType,
)
from app.modes import (
    MODE_REGISTRY, CustomMode, EcosystemMode, MemeticPhysicsMode, SyntheticCivMode,
    MarketDynamicsMode, PublicDiscourseMode, KnowledgeEcosystemsMode, EcologicalSystemsMode,
)


def _node(nid, ntype=NodeType.AGENT, **kw):
    return GraphNode(
        node_id=nid, node_type=ntype, label=nid,
        state=NodeState(**kw),
    )


def _edge(eid, src, tgt, etype=EdgeType.INFLUENCE, **kw):
    return GraphEdge(
        edge_id=eid, source_id=src, target_id=tgt,
        edge_type=etype, **kw,
    )


class TestModeRegistry:
    def test_all_modes_registered(self):
        assert len(MODE_REGISTRY) == 8

    def test_all_modes_have_name(self):
        for name, cls in MODE_REGISTRY.items():
            m = cls()
            assert m.name == name

    def test_all_modes_serializable(self):
        for cls in MODE_REGISTRY.values():
            d = cls().to_dict()
            assert "name" in d
            assert "description" in d
            assert "required_templates" in d


class TestCustomMode:
    def test_passthrough(self):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        m = CustomMode()
        result = m.initialize_graph(g)
        assert result is g

    def test_no_required_templates(self):
        m = CustomMode()
        assert m.get_templates() == []


class TestSyntheticCivMode:
    def test_initialize_assigns_positions(self):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        m = SyntheticCivMode()
        m.initialize_graph(g)
        a = g.get_node("a")
        assert len(a.state.ideological_position) == 2

    def test_post_step_forms_institution(self):
        g = DynamicsGraph()
        for i in range(4):
            g.add_node(_node(f"agent{i}"))
        # Fully connect with high-weight edges
        for i in range(4):
            for j in range(4):
                if i != j:
                    g.add_edge(_edge(
                        f"e{i}{j}", f"agent{i}", f"agent{j}",
                        weight=1.0,
                    ))
        m = SyntheticCivMode()
        events = m.post_step_hook(g, 10)
        assert len(events) > 0
        assert events[0]["event_type"] == "institution_formed"

    def test_no_institution_when_low_weight(self):
        g = DynamicsGraph()
        for i in range(4):
            g.add_node(_node(f"a{i}"))
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(_edge(f"e{i}{j}", f"a{i}", f"a{j}", weight=0.1))
        m = SyntheticCivMode()
        events = m.post_step_hook(g, 10)
        assert len(events) == 0

    def test_required_templates(self):
        m = SyntheticCivMode()
        templates = m.get_templates()
        assert "diffusion" in templates
        assert "opinion" in templates


class TestEcosystemMode:
    def test_initialize_boosts_mutation(self):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        m = EcosystemMode()
        m.initialize_graph(g)
        assert g.get_node("a").state.mutation_rate == 0.03

    def test_extinction_event(self):
        g = DynamicsGraph()
        g.add_node(_node("dying", energy=0.01))
        m = EcosystemMode()
        events = m.post_step_hook(g, 5)
        assert any(e["event_type"] == "extinction" for e in events)

    def test_reproduction_event(self):
        g = DynamicsGraph()
        g.add_node(_node("thriving", energy=10.0))
        m = EcosystemMode()
        events = m.post_step_hook(g, 5)
        assert any(e["event_type"] == "reproduction" for e in events)


class TestMemeticPhysicsMode:
    def test_initialize_positions_ideas(self):
        g = DynamicsGraph()
        g.add_node(_node("idea1", NodeType.IDEA))
        m = MemeticPhysicsMode()
        m.initialize_graph(g)
        idea = g.get_node("idea1")
        assert len(idea.state.ideological_position) == 2
        assert idea.state.energy == 2.0

    def test_gravity_well_event(self):
        g = DynamicsGraph()
        g.add_node(_node("big", NodeType.IDEA, energy=100.0))
        g.add_node(_node("small", NodeType.IDEA, energy=1.0))
        m = MemeticPhysicsMode()
        events = m.post_step_hook(g, 10)
        assert any(e["event_type"] == "gravity_well" for e in events)


class TestMarketDynamicsMode:
    def test_initialize_boosts_institutions(self):
        g = DynamicsGraph()
        g.add_node(_node("corp", NodeType.INSTITUTION))
        m = MarketDynamicsMode()
        m.initialize_graph(g)
        assert g.get_node("corp").state.resources == 8.0

    def test_market_concentration_event(self):
        g = DynamicsGraph()
        g.add_node(_node("big_corp", NodeType.INSTITUTION, resources=90.0))
        g.add_node(_node("small_corp", NodeType.INSTITUTION, resources=10.0))
        m = MarketDynamicsMode()
        events = m.post_step_hook(g, 10)
        assert any(e["event_type"] == "market_concentration" for e in events)


class TestPublicDiscourseMode:
    def test_initialize_assigns_positions(self):
        g = DynamicsGraph()
        g.add_node(_node("voter"))
        m = PublicDiscourseMode()
        m.initialize_graph(g)
        assert len(g.get_node("voter").state.ideological_position) == 2

    def test_polarization_event(self):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"left{i}", ideological_position=[0.0, 0.5]))
        for i in range(5):
            g.add_node(_node(f"right{i}", ideological_position=[1.0, 0.5]))
        m = PublicDiscourseMode()
        events = m.post_step_hook(g, 10)
        assert any(e["event_type"] == "polarization_spike" for e in events)


class TestKnowledgeEcosystemsMode:
    def test_initialize_sets_idea_energy(self):
        g = DynamicsGraph()
        g.add_node(_node("paper1", NodeType.IDEA))
        m = KnowledgeEcosystemsMode()
        m.initialize_graph(g)
        assert g.get_node("paper1").state.energy > 1.0

    def test_paradigm_competition(self):
        g = DynamicsGraph()
        g.add_node(_node("theory_a", NodeType.IDEA, energy=5.0))
        g.add_node(_node("theory_b", NodeType.IDEA, energy=4.8))
        m = KnowledgeEcosystemsMode()
        events = m.post_step_hook(g, 10)
        assert any(e["event_type"] == "paradigm_competition" for e in events)


class TestEcologicalSystemsMode:
    def test_initialize_boosts_resources(self):
        g = DynamicsGraph()
        g.add_node(_node("forest", NodeType.RESOURCE))
        m = EcologicalSystemsMode()
        m.initialize_graph(g)
        assert g.get_node("forest").state.resources == 12.0

    def test_habitat_collapse_event(self):
        g = DynamicsGraph()
        g.add_node(_node("degraded", NodeType.RESOURCE, resources=0.5, stability=0.5))
        m = EcologicalSystemsMode()
        events = m.post_step_hook(g, 10)
        assert any(e["event_type"] == "habitat_collapse" for e in events)

    def test_species_endangered_event(self):
        g = DynamicsGraph()
        g.add_node(_node("rare_bird", energy=0.05))
        m = EcologicalSystemsMode()
        events = m.post_step_hook(g, 10)
        assert any(e["event_type"] == "species_endangered" for e in events)


# ---------------------------------------------------------------------------
# API tests for mode endpoints
# ---------------------------------------------------------------------------


SAMPLE_GRAPH_DATA = {
    "nodes": [
        {"uuid": "u1", "name": "Alice", "labels": ["Person"], "summary": "", "attributes": {}},
        {"uuid": "u2", "name": "Bob", "labels": ["Person"], "summary": "", "attributes": {}},
    ],
    "edges": [
        {
            "uuid": "e1", "name": "supports", "fact": "Alice supports Bob",
            "fact_type": "SUPPORTS", "source_node_uuid": "u1", "target_node_uuid": "u2",
            "attributes": {},
        },
    ],
}


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sim_id(client):
    resp = client.post(
        "/api/dynamics/initialize",
        data=json.dumps({"graph_data": SAMPLE_GRAPH_DATA}),
        content_type="application/json",
    )
    return resp.get_json()["sim_id"]


class TestModeAPI:
    def test_list_modes(self, client):
        resp = client.get("/api/dynamics/modes")
        assert resp.status_code == 200
        body = resp.get_json()
        names = {m["name"] for m in body}
        assert "custom" in names
        assert "synthetic_civ" in names
        assert "ecosystem" in names
        assert "memetic_physics" in names

    def test_apply_mode(self, client, sim_id):
        resp = client.post(
            "/api/dynamics/modes/synthetic_civ/apply",
            data=json.dumps({"sim_id": sim_id}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["mode"] == "synthetic_civ"
        assert body["status"] == "configured"
        assert "diffusion" in body["templates"]

    def test_apply_unknown_mode(self, client, sim_id):
        resp = client.post(
            "/api/dynamics/modes/nonexistent/apply",
            data=json.dumps({"sim_id": sim_id}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_apply_mode_then_start(self, client, sim_id):
        client.post(
            "/api/dynamics/modes/ecosystem/apply",
            data=json.dumps({"sim_id": sim_id}),
            content_type="application/json",
        )
        resp = client.post(
            "/api/dynamics/start",
            data=json.dumps({"sim_id": sim_id, "steps": 5}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        import time
        time.sleep(0.5)
        resp = client.get(f"/api/dynamics/status/{sim_id}")
        assert resp.get_json()["status"] in ("completed", "running")
