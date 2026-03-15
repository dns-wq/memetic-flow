"""Tests for the measurement & observation layer."""

import pytest

from app.dynamics import (
    DynamicsGraph,
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeState,
    NodeType,
)
from app.metrics import MetricsCollector, PhaseTransitionDetector


def _node(nid, ntype=NodeType.AGENT, institution_id=None, **kw):
    return GraphNode(node_id=nid, node_type=ntype, label=nid, state=NodeState(**kw), institution_id=institution_id)

def _edge(eid, src, tgt, etype=EdgeType.INFLUENCE, **kw):
    return GraphEdge(edge_id=eid, source_id=src, target_id=tgt, edge_type=etype, **kw)


class TestMetricsCollector:
    @pytest.fixture
    def collector(self):
        return MetricsCollector()

    def test_compute_returns_all_keys(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        metrics = collector.compute(g)
        expected_keys = {
            "idea_entropy", "polarization_index", "clustering_coefficient",
            "institutional_cohesion", "resource_gini", "cascade_count",
            "feedback_loop_strength", "total_energy", "num_nodes", "num_edges",
        }
        assert set(metrics.keys()) == expected_keys

    def test_entropy_equal_distribution(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("i1", NodeType.IDEA, energy=1.0))
        g.add_node(_node("i2", NodeType.IDEA, energy=1.0))
        g.add_node(_node("i3", NodeType.IDEA, energy=1.0))
        g.add_node(_node("i4", NodeType.IDEA, energy=1.0))
        metrics = collector.compute(g)
        # 4 equally energetic ideas → entropy = log2(4) = 2.0
        assert abs(metrics["idea_entropy"] - 2.0) < 0.01

    def test_entropy_single_dominant(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("i1", NodeType.IDEA, energy=100.0))
        g.add_node(_node("i2", NodeType.IDEA, energy=0.001))
        metrics = collector.compute(g)
        # Dominated by one idea → low entropy
        assert metrics["idea_entropy"] < 0.1

    def test_gini_equal(self, collector):
        g = DynamicsGraph()
        for i in range(10):
            g.add_node(_node(f"n{i}", resources=5.0))
        metrics = collector.compute(g)
        assert abs(metrics["resource_gini"]) < 0.01  # Perfect equality

    def test_gini_unequal(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("rich", resources=100.0))
        for i in range(9):
            g.add_node(_node(f"poor{i}", resources=0.0))
        metrics = collector.compute(g)
        assert metrics["resource_gini"] > 0.8  # High inequality

    def test_clustering_triangle(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_node(_node("c"))
        g.add_edge(_edge("ab", "a", "b"))
        g.add_edge(_edge("bc", "b", "c"))
        g.add_edge(_edge("ca", "c", "a"))
        metrics = collector.compute(g)
        # Complete triangle → clustering = 1.0
        assert metrics["clustering_coefficient"] == 1.0

    def test_clustering_no_triangles(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_node(_node("c"))
        g.add_edge(_edge("ab", "a", "b"))
        g.add_edge(_edge("ac", "a", "c"))
        # Star topology: no triangles
        metrics = collector.compute(g)
        assert metrics["clustering_coefficient"] == 0.0

    def test_polarization_consensus(self, collector):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"a{i}", ideological_position=[0.5]))
        metrics = collector.compute(g)
        assert metrics["polarization_index"] == 0.0

    def test_polarization_two_camps(self, collector):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"left{i}", ideological_position=[0.0]))
        for i in range(5):
            g.add_node(_node(f"right{i}", ideological_position=[1.0]))
        metrics = collector.compute(g)
        assert metrics["polarization_index"] > 0.3

    def test_institutional_cohesion(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("a", institution_id="inst"))
        g.add_node(_node("b", institution_id="inst"))
        g.add_node(_node("c", institution_id="inst"))
        # Fully connected within institution
        g.add_edge(_edge("ab", "a", "b"))
        g.add_edge(_edge("ba", "b", "a"))
        g.add_edge(_edge("bc", "b", "c"))
        g.add_edge(_edge("cb", "c", "b"))
        g.add_edge(_edge("ac", "a", "c"))
        g.add_edge(_edge("ca", "c", "a"))
        metrics = collector.compute(g)
        assert metrics["institutional_cohesion"] == 1.0

    def test_cascade_count(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("normal1", energy=1.0))
        g.add_node(_node("normal2", energy=1.0))
        g.add_node(_node("cascade", energy=10.0))
        metrics = collector.compute(g)
        assert metrics["cascade_count"] == 1.0  # only "cascade" is >2x mean

    def test_total_energy(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("a", energy=3.0))
        g.add_node(_node("b", energy=7.0))
        metrics = collector.compute(g)
        assert metrics["total_energy"] == 10.0

    def test_feedback_loop_strength(self, collector):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("ab", "a", "b", weight=2.0))
        g.add_edge(_edge("ba", "b", "a", weight=4.0))
        metrics = collector.compute(g)
        # Loop a→b→a with weights 2.0 and 4.0 → avg 3.0
        assert metrics["feedback_loop_strength"] == 3.0


class TestPhaseTransitionDetector:
    def test_no_events_for_stable_series(self):
        d = PhaseTransitionDetector(derivative_threshold=2.0, window_size=3)
        for t in range(20):
            events = d.update({"entropy": 1.0}, t)
        assert len(events) == 0

    def test_spike_detected(self):
        d = PhaseTransitionDetector(derivative_threshold=1.0, window_size=3)
        all_events = []
        for t in range(10):
            val = 1.0 if t < 7 else 10.0
            events = d.update({"entropy": val}, t)
            all_events.extend(events)
        assert len(all_events) > 0
        assert all_events[0].event_type == "spike"

    def test_drop_detected(self):
        d = PhaseTransitionDetector(derivative_threshold=0.5, window_size=3)
        all_events = []
        for t in range(15):
            val = 10.0 if t < 8 else 1.0
            events = d.update({"entropy": val}, t)
            all_events.extend(events)
        assert any(e.event_type == "drop" for e in all_events)

    def test_reset_clears_history(self):
        d = PhaseTransitionDetector()
        d.update({"x": 1.0}, 0)
        d.reset()
        assert d._history == {}
