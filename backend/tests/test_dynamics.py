"""Tests for the typed graph data model, DynamicsGraph, and persistence."""

import os
import tempfile

import pytest

from app.dynamics import (
    DynamicsGraph,
    DynamicsStore,
    EdgeType,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    NodeState,
    NodeType,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def _make_node(node_id: str, ntype: NodeType = NodeType.AGENT, **kw) -> GraphNode:
    return GraphNode(node_id=node_id, node_type=ntype, label=node_id, **kw)


def _make_edge(
    edge_id: str,
    src: str,
    tgt: str,
    etype: EdgeType = EdgeType.INFLUENCE,
    **kw,
) -> GraphEdge:
    return GraphEdge(edge_id=edge_id, source_id=src, target_id=tgt, edge_type=etype, **kw)


@pytest.fixture
def triangle_graph() -> DynamicsGraph:
    """A → B → C → A triangle with 3 agent nodes."""
    g = DynamicsGraph()
    g.add_node(_make_node("a"))
    g.add_node(_make_node("b"))
    g.add_node(_make_node("c"))
    g.add_edge(_make_edge("ab", "a", "b"))
    g.add_edge(_make_edge("bc", "b", "c"))
    g.add_edge(_make_edge("ca", "c", "a"))
    return g


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

class TestModels:
    def test_node_state_defaults(self):
        state = NodeState()
        assert state.resources == 1.0
        assert state.energy == 1.0
        assert state.ideological_position == []
        assert state.custom == {}

    def test_node_creation_auto_id(self):
        node = GraphNode(node_type=NodeType.IDEA, label="test")
        assert len(node.node_id) == 12
        assert node.node_type == NodeType.IDEA

    def test_edge_creation(self):
        edge = GraphEdge(
            source_id="a", target_id="b", edge_type=EdgeType.INFORMATION, weight=0.5
        )
        assert edge.weight == 0.5
        assert edge.edge_type == EdgeType.INFORMATION

    def test_snapshot_creation(self):
        snap = GraphSnapshot(timestep=0, nodes={}, edges={})
        assert snap.timestep == 0
        assert snap.metrics == {}


# ------------------------------------------------------------------
# DynamicsGraph — node/edge CRUD
# ------------------------------------------------------------------

class TestGraphCRUD:
    def test_add_and_get_node(self):
        g = DynamicsGraph()
        n = _make_node("x")
        g.add_node(n)
        assert g.has_node("x")
        assert g.get_node("x").label == "x"

    def test_add_duplicate_node_raises(self):
        g = DynamicsGraph()
        g.add_node(_make_node("x"))
        with pytest.raises(ValueError):
            g.add_node(_make_node("x"))

    def test_remove_node_cascades_edges(self, triangle_graph):
        triangle_graph.remove_node("b")
        assert not triangle_graph.has_node("b")
        # edges ab and bc should be gone
        assert len(triangle_graph.edges) == 1
        assert "ca" in triangle_graph.edges

    def test_add_edge_missing_node_raises(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a"))
        with pytest.raises(KeyError):
            g.add_edge(_make_edge("ax", "a", "missing"))

    def test_remove_edge(self, triangle_graph):
        triangle_graph.remove_edge("ab")
        assert "ab" not in triangle_graph.edges
        assert len(triangle_graph.edges) == 2

    def test_nodes_by_type(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a", NodeType.AGENT))
        g.add_node(_make_node("i", NodeType.IDEA))
        g.add_node(_make_node("r", NodeType.RESOURCE))
        assert len(g.nodes_by_type(NodeType.AGENT)) == 1
        assert len(g.nodes_by_type(NodeType.IDEA)) == 1

    def test_update_node_state(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a"))
        g.update_node_state("a", energy=5.0, influence=0.9)
        assert g.get_node("a").state.energy == 5.0
        assert g.get_node("a").state.influence == 0.9

    def test_update_node_custom(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a"))
        g.update_node_custom("a", sentiment=0.7, trust=0.3)
        assert g.get_node("a").state.custom["sentiment"] == 0.7


# ------------------------------------------------------------------
# DynamicsGraph — topology queries
# ------------------------------------------------------------------

class TestGraphTopology:
    def test_get_neighbors_out(self, triangle_graph):
        out = triangle_graph.get_neighbors("a", "out")
        assert out == ["b"]

    def test_get_neighbors_in(self, triangle_graph):
        incoming = triangle_graph.get_neighbors("a", "in")
        assert incoming == ["c"]

    def test_get_neighbors_both(self, triangle_graph):
        both = set(triangle_graph.get_neighbors("a", "both"))
        assert both == {"b", "c"}

    def test_get_neighbors_filtered_by_edge_type(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a"))
        g.add_node(_make_node("b"))
        g.add_node(_make_node("c"))
        g.add_edge(_make_edge("ab", "a", "b", EdgeType.INFLUENCE))
        g.add_edge(_make_edge("ac", "a", "c", EdgeType.INFORMATION))
        out_inf = g.get_neighbors("a", "out", edge_type=EdgeType.INFLUENCE)
        assert out_inf == ["b"]

    def test_get_edges_between(self, triangle_graph):
        edges = triangle_graph.get_edges_between("a", "b")
        assert len(edges) == 1
        assert edges[0].edge_id == "ab"

    def test_feedback_loop_detection(self, triangle_graph):
        loops = triangle_graph.get_feedback_loops(max_length=3)
        assert len(loops) == 1
        assert set(loops[0]) == {"a", "b", "c"}

    def test_no_loops_in_dag(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a"))
        g.add_node(_make_node("b"))
        g.add_node(_make_node("c"))
        g.add_edge(_make_edge("ab", "a", "b"))
        g.add_edge(_make_edge("bc", "b", "c"))
        loops = g.get_feedback_loops()
        assert loops == []


# ------------------------------------------------------------------
# DynamicsGraph — institutions
# ------------------------------------------------------------------

class TestInstitutions:
    def test_institution_via_node(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a", institution_id="inst1"))
        g.add_node(_make_node("b", institution_id="inst1"))
        members = g.get_institution_members("inst1")
        assert set(members) == {"a", "b"}

    def test_assign_institution(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a"))
        g.assign_institution("a", "inst1")
        assert g.get_node("a").institution_id == "inst1"
        assert "a" in g.get_institution_members("inst1")

    def test_reassign_institution(self):
        g = DynamicsGraph()
        g.add_node(_make_node("a", institution_id="old"))
        g.assign_institution("a", "new")
        assert g.get_institution_members("old") == []
        assert "a" in g.get_institution_members("new")


# ------------------------------------------------------------------
# DynamicsGraph — snapshots & timeline
# ------------------------------------------------------------------

class TestSnapshots:
    def test_snapshot_is_deep_copy(self, triangle_graph):
        snap = triangle_graph.snapshot()
        # Mutate the live graph
        triangle_graph.update_node_state("a", energy=999.0)
        # Snapshot should be unaffected
        assert snap.nodes["a"].state.energy == 1.0

    def test_save_and_replay(self, triangle_graph):
        triangle_graph.save_snapshot()
        triangle_graph.update_node_state("a", energy=10.0)
        triangle_graph.advance_timestep()
        triangle_graph.save_snapshot()
        assert len(triangle_graph.history) == 2
        assert triangle_graph.history[0].nodes["a"].state.energy == 1.0
        assert triangle_graph.history[1].nodes["a"].state.energy == 10.0

    def test_restore_from_snapshot(self, triangle_graph):
        snap = triangle_graph.snapshot()
        triangle_graph.update_node_state("a", energy=999.0)
        triangle_graph.remove_node("b")
        triangle_graph.restore(snap)
        assert triangle_graph.get_node("a").state.energy == 1.0
        assert triangle_graph.has_node("b")

    def test_seed_constructor(self, triangle_graph):
        snap = triangle_graph.snapshot()
        g2 = DynamicsGraph(seed=snap)
        assert g2.has_node("a")
        assert len(g2.edges) == 3
        # Mutating g2 doesn't affect original snap
        g2.update_node_state("a", energy=42.0)
        assert snap.nodes["a"].state.energy == 1.0

    def test_summary(self, triangle_graph):
        s = triangle_graph.summary()
        assert s["num_nodes"] == 3
        assert s["num_edges"] == 3
        assert s["node_types"]["agent"] == 3


# ------------------------------------------------------------------
# Persistence — DynamicsStore
# ------------------------------------------------------------------

class TestPersistence:
    @pytest.fixture
    def store(self, tmp_path):
        db_path = str(tmp_path / "test_dynamics.db")
        return DynamicsStore(db_path=db_path)

    def test_save_and_load_snapshot(self, store, triangle_graph):
        snap = triangle_graph.snapshot()
        snap.metrics = {"entropy": 1.5, "gini": 0.3}
        store.save_snapshot("sim1", snap)

        loaded = store.load_snapshot("sim1", 0)
        assert loaded is not None
        assert loaded.timestep == 0
        assert set(loaded.nodes.keys()) == {"a", "b", "c"}
        assert set(loaded.edges.keys()) == {"ab", "bc", "ca"}
        assert loaded.metrics["entropy"] == 1.5

    def test_load_missing_returns_none(self, store):
        assert store.load_snapshot("nonexistent", 0) is None

    def test_load_latest_snapshot(self, store, triangle_graph):
        snap0 = triangle_graph.snapshot()
        store.save_snapshot("sim1", snap0)

        triangle_graph.advance_timestep()
        triangle_graph.update_node_state("a", energy=5.0)
        snap1 = triangle_graph.snapshot()
        store.save_snapshot("sim1", snap1)

        latest = store.load_latest_snapshot("sim1")
        assert latest.timestep == 1
        assert latest.nodes["a"].state.energy == 5.0

    def test_load_all_snapshots(self, store, triangle_graph):
        for i in range(3):
            snap = triangle_graph.snapshot()
            store.save_snapshot("sim1", snap)
            triangle_graph.advance_timestep()
        assert store.snapshot_count("sim1") == 3
        all_snaps = store.load_all_snapshots("sim1")
        assert [s.timestep for s in all_snaps] == [0, 1, 2]

    def test_metric_series(self, store, triangle_graph):
        for i in range(5):
            snap = triangle_graph.snapshot()
            snap.metrics = {"entropy": float(i) * 0.1}
            store.save_snapshot("sim1", snap)
            triangle_graph.advance_timestep()

        series = store.get_metric_series("sim1", "entropy")
        assert len(series) == 5
        assert series[0] == (0, 0.0)
        assert series[4] == (4, 0.4)

    def test_available_metrics(self, store, triangle_graph):
        snap = triangle_graph.snapshot()
        snap.metrics = {"entropy": 1.0, "gini": 0.5}
        store.save_snapshot("sim1", snap)
        available = store.get_available_metrics("sim1")
        assert set(available) == {"entropy", "gini"}

    def test_delete_simulation(self, store, triangle_graph):
        snap = triangle_graph.snapshot()
        snap.metrics = {"x": 1.0}
        store.save_snapshot("sim1", snap)
        store.delete_simulation("sim1")
        assert store.snapshot_count("sim1") == 0
        assert store.get_available_metrics("sim1") == []

    def test_snapshot_round_trip_preserves_types(self, store):
        """Ensure node/edge types survive serialization."""
        g = DynamicsGraph()
        g.add_node(GraphNode(
            node_id="idea1",
            node_type=NodeType.IDEA,
            label="Meme X",
            state=NodeState(energy=3.5, ideological_position=[0.1, -0.2]),
        ))
        g.add_node(GraphNode(
            node_id="agent1",
            node_type=NodeType.AGENT,
            label="Alice",
            state=NodeState(influence=0.8, custom={"trust": 0.9}),
            institution_id="inst1",
        ))
        g.add_edge(GraphEdge(
            edge_id="e1",
            source_id="agent1",
            target_id="idea1",
            edge_type=EdgeType.INFORMATION,
            weight=2.0,
            transfer_rate=0.05,
        ))

        snap = g.snapshot()
        snap.institutions = {"inst1": ["agent1"]}
        store.save_snapshot("roundtrip", snap)

        loaded = store.load_snapshot("roundtrip", 0)
        assert loaded.nodes["idea1"].node_type == NodeType.IDEA
        assert loaded.nodes["idea1"].state.energy == 3.5
        assert loaded.nodes["idea1"].state.ideological_position == [0.1, -0.2]
        assert loaded.nodes["agent1"].state.custom["trust"] == 0.9
        assert loaded.nodes["agent1"].institution_id == "inst1"
        assert loaded.edges["e1"].edge_type == EdgeType.INFORMATION
        assert loaded.edges["e1"].weight == 2.0
        assert loaded.institutions == {"inst1": ["agent1"]}
