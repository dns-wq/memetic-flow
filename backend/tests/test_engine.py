"""Tests for the dynamical simulation engine and all template families."""

import numpy as np
import pytest

from app.dynamics import (
    DynamicsGraph,
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeState,
    NodeType,
)
from app.engine import SimulationEngine, TEMPLATE_REGISTRY
from app.engine.templates import (
    DiffusionTemplate,
    OpinionTemplate,
    EvolutionaryTemplate,
    ResourceTemplate,
    FeedbackTemplate,
    ContagionTemplate,
    GameTheoryTemplate,
    NetworkEvolutionTemplate,
    MemoryLandscapeTemplate,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _node(nid: str, ntype: NodeType = NodeType.AGENT, **state_kw) -> GraphNode:
    return GraphNode(
        node_id=nid, node_type=ntype, label=nid,
        state=NodeState(**state_kw),
    )

def _edge(eid: str, src: str, tgt: str, etype: EdgeType = EdgeType.INFLUENCE, **kw) -> GraphEdge:
    return GraphEdge(edge_id=eid, source_id=src, target_id=tgt, edge_type=etype, **kw)


# ------------------------------------------------------------------
# Template registry
# ------------------------------------------------------------------

class TestTemplateRegistry:
    def test_all_registered(self):
        assert set(TEMPLATE_REGISTRY.keys()) == {
            "diffusion", "opinion", "evolutionary", "resource", "feedback",
            "contagion", "game_theory", "network_evolution", "memory_landscape",
        }

    def test_instances_have_required_attrs(self):
        for name, cls in TEMPLATE_REGISTRY.items():
            t = cls()
            assert t.name == name
            assert isinstance(t.parameters, dict)
            assert len(t.get_empirical_priors()) > 0


# ------------------------------------------------------------------
# Diffusion template
# ------------------------------------------------------------------

class TestDiffusion:
    def test_energy_spreads_to_neighbor(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=10.0))
        g.add_node(_node("b", NodeType.IDEA, energy=0.0))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFORMATION, weight=1.0, transfer_rate=1.0))

        t = DiffusionTemplate()
        rng = np.random.default_rng(0)
        t.update(g, {"transfer_rate": 0.5, "decay_rate": 0.0, "noise_std": 0.0}, rng)

        assert g.get_node("b").state.energy > 0.0

    def test_decay_reduces_energy(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=10.0))

        t = DiffusionTemplate()
        rng = np.random.default_rng(0)
        t.update(g, {"decay_rate": 0.1, "transfer_rate": 0.0, "noise_std": 0.0}, rng)

        assert g.get_node("a").state.energy < 10.0

    def test_threshold_blocks_weak_signals(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=0.05))
        g.add_node(_node("b", NodeType.IDEA, energy=0.0))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFORMATION, weight=1.0, transfer_rate=1.0))

        t = DiffusionTemplate()
        rng = np.random.default_rng(0)
        t.update(g, {"transfer_rate": 1.0, "decay_rate": 0.0, "threshold": 0.5, "noise_std": 0.0}, rng)

        # Node a's energy is below threshold, so b should get nothing
        assert g.get_node("b").state.energy == 0.0


# ------------------------------------------------------------------
# Opinion dynamics template
# ------------------------------------------------------------------

class TestOpinion:
    def test_close_opinions_converge(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.AGENT, ideological_position=[0.0]))
        g.add_node(_node("b", NodeType.AGENT, ideological_position=[0.2]))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFLUENCE))
        g.add_edge(_edge("ba", "b", "a", EdgeType.INFLUENCE))

        t = OpinionTemplate()
        rng = np.random.default_rng(0)
        for _ in range(20):
            t.update(g, {"tolerance": 0.5, "convergence_rate": 0.3, "noise_std": 0.0}, rng)

        pos_a = g.get_node("a").state.ideological_position[0]
        pos_b = g.get_node("b").state.ideological_position[0]
        assert abs(pos_a - pos_b) < 0.01  # Should have converged

    def test_distant_opinions_stay_apart(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.AGENT, ideological_position=[0.0]))
        g.add_node(_node("b", NodeType.AGENT, ideological_position=[1.0]))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFLUENCE))
        g.add_edge(_edge("ba", "b", "a", EdgeType.INFLUENCE))

        t = OpinionTemplate()
        rng = np.random.default_rng(0)
        for _ in range(20):
            t.update(g, {"tolerance": 0.1, "convergence_rate": 0.3, "noise_std": 0.0}, rng)

        pos_a = g.get_node("a").state.ideological_position[0]
        pos_b = g.get_node("b").state.ideological_position[0]
        # Should NOT have converged because distance > tolerance
        assert abs(pos_a - pos_b) > 0.5


# ------------------------------------------------------------------
# Evolutionary template
# ------------------------------------------------------------------

class TestEvolutionary:
    def test_fitter_ideas_grow(self):
        g = DynamicsGraph()
        # Idea A has more incoming edges (higher fitness)
        g.add_node(_node("idea_a", NodeType.IDEA, energy=1.0))
        g.add_node(_node("idea_b", NodeType.IDEA, energy=1.0))
        g.add_node(_node("agent1", NodeType.AGENT))
        g.add_node(_node("agent2", NodeType.AGENT))
        g.add_node(_node("agent3", NodeType.AGENT))
        g.add_edge(_edge("e1", "agent1", "idea_a", EdgeType.INFLUENCE))
        g.add_edge(_edge("e2", "agent2", "idea_a", EdgeType.INFLUENCE))
        g.add_edge(_edge("e3", "agent3", "idea_a", EdgeType.INFLUENCE))
        g.add_edge(_edge("e4", "agent1", "idea_b", EdgeType.INFLUENCE))

        t = EvolutionaryTemplate()
        rng = np.random.default_rng(42)
        for _ in range(10):
            t.update(g, {"selection_strength": 0.3, "mutation_rate": 0.0}, rng)

        # Idea A should have more energy than B
        assert g.get_node("idea_a").state.energy > g.get_node("idea_b").state.energy

    def test_carrying_capacity_respected(self):
        g = DynamicsGraph()
        g.add_node(_node("i1", NodeType.IDEA, energy=50.0))
        g.add_node(_node("i2", NodeType.IDEA, energy=50.0))

        t = EvolutionaryTemplate()
        rng = np.random.default_rng(0)
        t.update(g, {"carrying_capacity": 10.0, "mutation_rate": 0.0}, rng)

        total = g.get_node("i1").state.energy + g.get_node("i2").state.energy
        assert total <= 10.0 + 0.01  # Allow tiny float error


# ------------------------------------------------------------------
# Resource flow template
# ------------------------------------------------------------------

class TestResource:
    def test_resources_flow_along_edges(self):
        g = DynamicsGraph()
        g.add_node(_node("src", NodeType.RESOURCE, resources=10.0))
        g.add_node(_node("dst", NodeType.RESOURCE, resources=0.0))
        g.add_edge(_edge("flow", "src", "dst", EdgeType.RESOURCE_FLOW, weight=1.0, transfer_rate=1.0))

        t = ResourceTemplate()
        rng = np.random.default_rng(0)
        t.update(g, {"flow_rate": 0.5, "growth_rate": 0.0, "competition_coefficient": 0.0}, rng)

        assert g.get_node("dst").state.resources > 0.0
        assert g.get_node("src").state.resources < 10.0

    def test_logistic_growth(self):
        g = DynamicsGraph()
        g.add_node(_node("r", NodeType.RESOURCE, resources=1.0))

        t = ResourceTemplate()
        rng = np.random.default_rng(0)
        for _ in range(50):
            t.update(g, {"growth_rate": 0.1, "competition_coefficient": 0.0, "flow_rate": 0.0, "carrying_capacity": 10.0}, rng)

        # Should have grown toward carrying capacity
        assert g.get_node("r").state.resources > 5.0
        assert g.get_node("r").state.resources <= 10.0


# ------------------------------------------------------------------
# Feedback systems template
# ------------------------------------------------------------------

class TestFeedback:
    def test_stability_flows_between_nodes(self):
        g = DynamicsGraph()
        g.add_node(_node("a", stability=10.0))
        g.add_node(_node("b", stability=0.0))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFLUENCE, weight=1.0, transfer_rate=1.0))

        t = FeedbackTemplate()
        rng = np.random.default_rng(0)
        t.update(g, {"flow_coefficient": 0.5, "damping": 0.0, "saturation_limit": 50.0}, rng)

        assert g.get_node("b").state.stability > 0.0
        assert g.get_node("a").state.stability < 10.0

    def test_saturation_limits_accumulation(self):
        g = DynamicsGraph()
        g.add_node(_node("a", stability=100.0))
        g.add_node(_node("b", stability=49.0))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFLUENCE, weight=1.0, transfer_rate=1.0))

        t = FeedbackTemplate()
        rng = np.random.default_rng(0)
        t.update(g, {"flow_coefficient": 1.0, "damping": 0.0, "saturation_limit": 50.0}, rng)

        # b is near saturation, so very little flow should arrive
        assert g.get_node("b").state.stability <= 50.0


# ------------------------------------------------------------------
# SimulationEngine
# ------------------------------------------------------------------

class TestSimulationEngine:
    def test_step_advances_timestep(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=5.0))
        engine = SimulationEngine(g, [DiffusionTemplate()])
        engine.step()
        assert g.timestep == 1

    def test_run_produces_snapshots(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=5.0))
        g.add_node(_node("b", NodeType.IDEA, energy=0.0))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFORMATION))

        engine = SimulationEngine(g, [DiffusionTemplate()])
        snapshots = engine.run(10)
        assert len(snapshots) == 10
        assert g.timestep == 10

    def test_reproducibility_with_same_seed(self):
        def run_sim(seed):
            g = DynamicsGraph()
            g.add_node(_node("a", NodeType.IDEA, energy=5.0))
            g.add_node(_node("b", NodeType.IDEA, energy=1.0))
            g.add_edge(_edge("ab", "a", "b", EdgeType.INFORMATION))
            engine = SimulationEngine(g, [DiffusionTemplate()], seed=seed)
            engine.run(20)
            return g.get_node("b").state.energy

        e1 = run_sim(42)
        e2 = run_sim(42)
        assert e1 == e2

    def test_multiple_templates_applied(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.AGENT, energy=5.0, stability=5.0, ideological_position=[0.0]))
        g.add_node(_node("b", NodeType.AGENT, energy=1.0, stability=1.0, ideological_position=[0.5]))
        g.add_edge(_edge("ab", "a", "b", EdgeType.INFLUENCE))
        g.add_edge(_edge("ba", "b", "a", EdgeType.INFLUENCE))

        engine = SimulationEngine(g, [OpinionTemplate(), FeedbackTemplate()])
        engine.run(5)

        # Both templates should have executed
        assert g.timestep == 5
        assert len(g.history) == 5

    def test_callback_invoked(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=1.0))

        calls = []
        engine = SimulationEngine(g, [DiffusionTemplate()])
        engine.run(3, callback=lambda i, snap: calls.append(i))
        assert calls == [1, 2, 3]

    def test_stop_during_run(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=1.0))

        engine = SimulationEngine(g, [DiffusionTemplate()])

        def stop_at_5(i, snap):
            if i >= 5:
                engine.stop()

        snaps = engine.run(100, callback=stop_at_5)
        assert len(snaps) == 5

    def test_set_and_get_params(self):
        g = DynamicsGraph()
        g.add_node(_node("a", NodeType.IDEA, energy=1.0))

        engine = SimulationEngine(g, [DiffusionTemplate()])
        engine.set_params("diffusion", {"decay_rate": 0.05})
        assert engine.get_params("diffusion")["decay_rate"] == 0.05

    def test_add_remove_template(self):
        g = DynamicsGraph()
        g.add_node(_node("a"))

        engine = SimulationEngine(g, [])
        engine.add_template(DiffusionTemplate())
        assert "diffusion" in engine.template_names
        engine.remove_template("diffusion")
        assert "diffusion" not in engine.template_names


# ------------------------------------------------------------------
# Contagion template
# ------------------------------------------------------------------

class TestContagion:
    def test_infection_spreads(self):
        g = DynamicsGraph()
        g.add_node(_node("infected", energy=1.0))
        g.add_node(_node("susceptible", energy=1.0))
        g.add_edge(_edge("e", "infected", "susceptible"))

        t = ContagionTemplate()
        rng = np.random.default_rng(42)

        # Manually set initial states
        g.get_node("infected").state.custom["contagion_state"] = 2.0  # I
        g.get_node("infected").state.custom["contagion_timer"] = 0.0
        g.get_node("susceptible").state.custom["contagion_state"] = 0.0  # S
        g.get_node("susceptible").state.custom["contagion_timer"] = 0.0

        # Run enough steps for infection to spread
        for _ in range(50):
            t.update(g, {"infection_rate": 0.8, "recovery_rate": 0.0, "immunity_duration": 0.0}, rng)

        # Susceptible should become infected
        assert int(g.get_node("susceptible").state.custom["contagion_state"]) == 2

    def test_recovery(self):
        g = DynamicsGraph()
        g.add_node(_node("patient", energy=1.0))

        t = ContagionTemplate()
        rng = np.random.default_rng(0)

        g.get_node("patient").state.custom["contagion_state"] = 2.0  # I
        g.get_node("patient").state.custom["contagion_timer"] = 0.0

        for _ in range(100):
            t.update(g, {"infection_rate": 0.0, "recovery_rate": 0.5, "immunity_duration": 0.0}, rng)

        assert int(g.get_node("patient").state.custom["contagion_state"]) == 3  # R

    def test_auto_initialisation(self):
        g = DynamicsGraph()
        for i in range(20):
            g.add_node(_node(f"n{i}"))

        t = ContagionTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {"initial_infected_frac": 0.2}, rng)

        states = [int(n.state.custom.get("contagion_state", 0)) for n in g.nodes.values()]
        assert 2 in states  # at least one infected

    def test_latent_period(self):
        g = DynamicsGraph()
        g.add_node(_node("infected", energy=1.0))
        g.add_node(_node("target", energy=1.0))
        g.add_edge(_edge("e", "infected", "target"))

        t = ContagionTemplate()
        rng = np.random.default_rng(0)

        g.get_node("infected").state.custom["contagion_state"] = 2.0
        g.get_node("infected").state.custom["contagion_timer"] = 0.0
        g.get_node("target").state.custom["contagion_state"] = 0.0
        g.get_node("target").state.custom["contagion_timer"] = 0.0

        # With high infection rate and latent period, target should go through E state
        params = {"infection_rate": 1.0, "recovery_rate": 0.0, "latent_period": 3.0, "immunity_duration": 0.0}
        t.update(g, params, rng)
        if int(g.get_node("target").state.custom["contagion_state"]) == 1:
            # In exposed state — verify it transitions to I after latent period
            for _ in range(5):
                t.update(g, params, rng)
            assert int(g.get_node("target").state.custom["contagion_state"]) == 2


# ------------------------------------------------------------------
# Game theory template
# ------------------------------------------------------------------

class TestGameTheory:
    def test_strategies_initialized(self):
        g = DynamicsGraph()
        for i in range(10):
            g.add_node(_node(f"a{i}"))
        for i in range(10):
            for j in range(i + 1, 10):
                g.add_edge(_edge(f"e{i}{j}", f"a{i}", f"a{j}"))

        t = GameTheoryTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        for n in g.nodes.values():
            assert "game_strategy" in n.state.custom
            assert n.state.custom["game_strategy"] in (0.0, 1.0)

    def test_payoffs_computed(self):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("ab", "a", "b"))

        t = GameTheoryTemplate()
        rng = np.random.default_rng(42)

        # Both cooperate
        g.get_node("a").state.custom["game_strategy"] = 0.0
        g.get_node("a").state.custom["game_payoff"] = 0.0
        g.get_node("b").state.custom["game_strategy"] = 0.0
        g.get_node("b").state.custom["game_payoff"] = 0.0

        t.update(g, {"payoff_cc": 3.0, "payoff_cd": 0.0, "payoff_dc": 5.0, "payoff_dd": 1.0}, rng)
        # Both played C against each other, payoff should be CC = 3.0
        assert g.get_node("a").state.custom["game_payoff"] == 3.0

    def test_defection_invasion(self):
        """In a PD, a defector among cooperators should spread."""
        g = DynamicsGraph()
        for i in range(10):
            g.add_node(_node(f"a{i}"))
        for i in range(10):
            for j in range(i + 1, 10):
                g.add_edge(_edge(f"e{i}{j}", f"a{i}", f"a{j}"))

        t = GameTheoryTemplate()
        rng = np.random.default_rng(42)

        # All cooperate except one
        for n in g.nodes.values():
            n.state.custom["game_strategy"] = 0.0
            n.state.custom["game_payoff"] = 0.0
        g.get_node("a0").state.custom["game_strategy"] = 1.0

        # Run many steps
        for _ in range(100):
            t.update(g, {"noise": 0.5}, rng)

        # Defection should have spread (at least some defectors)
        defectors = sum(
            1 for n in g.nodes.values()
            if int(n.state.custom["game_strategy"]) == 1
        )
        assert defectors > 1


# ------------------------------------------------------------------
# Network evolution template
# ------------------------------------------------------------------

class TestNetworkEvolution:
    def test_new_edges_formed(self):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"n{i}", ideological_position=[i * 0.2, 0.5]))

        initial_edges = len(g.edges)
        t = NetworkEvolutionTemplate()
        rng = np.random.default_rng(42)

        for _ in range(20):
            t.update(g, {"rewiring_probability": 0.5, "edge_decay_rate": 0.0}, rng)

        assert len(g.edges) > initial_edges

    def test_homophily_connects_similar(self):
        g = DynamicsGraph()
        # Two clusters far apart — many nodes to avoid saturation
        for i in range(20):
            g.add_node(_node(f"left{i}", ideological_position=[0.0, 0.0]))
        for i in range(20):
            g.add_node(_node(f"right{i}", ideological_position=[1.0, 1.0]))

        t = NetworkEvolutionTemplate()
        rng = np.random.default_rng(42)

        # Few iterations so intra-cluster edges don't saturate
        for _ in range(3):
            t.update(g, {
                "rewiring_probability": 0.5,
                "homophily_strength": 5.0,
                "triadic_closure_rate": 0.0,
                "edge_decay_rate": 0.0,
            }, rng)

        intra = 0
        inter = 0
        for e in g.edges.values():
            s_left = e.source_id.startswith("left")
            t_left = e.target_id.startswith("left")
            if s_left == t_left:
                intra += 1
            else:
                inter += 1
        assert intra > inter

    def test_edge_decay(self):
        g = DynamicsGraph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("weak", "a", "b", weight=0.05))

        t = NetworkEvolutionTemplate()
        rng = np.random.default_rng(42)

        for _ in range(50):
            t.update(g, {"rewiring_probability": 0.0, "edge_decay_rate": 0.5, "decay_weight_threshold": 0.2}, rng)

        assert len(g.edges) == 0

    def test_triadic_closure(self):
        g = DynamicsGraph()
        g.add_node(_node("a", ideological_position=[0.5, 0.5]))
        g.add_node(_node("b", ideological_position=[0.5, 0.5]))
        g.add_node(_node("c", ideological_position=[0.5, 0.5]))
        g.add_edge(_edge("ab", "a", "b", weight=0.8))
        g.add_edge(_edge("bc", "b", "c", weight=0.8))
        # a→b→c exists, but not a→c

        t = NetworkEvolutionTemplate()
        rng = np.random.default_rng(42)

        for _ in range(30):
            t.update(g, {
                "rewiring_probability": 0.8,
                "triadic_closure_rate": 0.9,
                "edge_decay_rate": 0.0,
            }, rng)

        # a↔c edge should have formed via triadic closure
        ac_edges = g.get_edges_between("a", "c") + g.get_edges_between("c", "a")
        assert len(ac_edges) > 0


# ------------------------------------------------------------------
# Memory landscape template
# ------------------------------------------------------------------

class TestMemoryLandscape:
    def test_memory_pool_created(self):
        g = DynamicsGraph()
        g.add_node(_node("writer", energy=5.0))

        t = MemoryLandscapeTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        assert g.has_node("__memory_pool__")
        pool = g.get_node("__memory_pool__")
        assert pool.node_type == NodeType.ENVIRONMENT

    def test_writing_increases_memory(self):
        g = DynamicsGraph()
        g.add_node(_node("writer", energy=5.0))

        t = MemoryLandscapeTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {"write_rate": 0.5, "memory_persistence": 1.0, "num_memory_slots": 4.0}, rng)

        pool = g.get_node("__memory_pool__")
        total = sum(pool.state.custom.get(f"mem_{i}", 0.0) for i in range(4))
        assert total > 0.0

    def test_memory_decays(self):
        g = DynamicsGraph()
        g.add_node(_node("writer", energy=5.0))

        t = MemoryLandscapeTemplate()
        rng = np.random.default_rng(42)

        # Write a strong memory
        t.update(g, {"write_rate": 1.0, "memory_persistence": 1.0, "num_memory_slots": 4.0}, rng)
        pool = g.get_node("__memory_pool__")
        total_before = sum(pool.state.custom.get(f"mem_{i}", 0.0) for i in range(4))

        # Now decay with no writing
        g.get_node("writer").state.energy = 0.0
        for _ in range(20):
            t.update(g, {"write_rate": 0.0, "memory_persistence": 0.5, "num_memory_slots": 4.0}, rng)

        total_after = sum(pool.state.custom.get(f"mem_{i}", 0.0) for i in range(4))
        assert total_after < total_before

    def test_resonance_amplifies(self):
        g = DynamicsGraph()
        g.add_node(_node("writer", energy=5.0))

        t = MemoryLandscapeTemplate()
        rng = np.random.default_rng(42)

        # Two rounds of writing — second should be amplified by resonance
        t.update(g, {
            "write_rate": 0.5,
            "memory_persistence": 1.0,
            "resonance_amplification": 3.0,
            "retrieval_threshold": 0.0,
            "num_memory_slots": 4.0,
        }, rng)
        pool = g.get_node("__memory_pool__")
        after_first = sum(pool.state.custom.get(f"mem_{i}", 0.0) for i in range(4))

        t.update(g, {
            "write_rate": 0.5,
            "memory_persistence": 1.0,
            "resonance_amplification": 3.0,
            "retrieval_threshold": 0.0,
            "num_memory_slots": 4.0,
        }, rng)
        after_second = sum(pool.state.custom.get(f"mem_{i}", 0.0) for i in range(4))

        # Second write should contribute more due to resonance
        increment = after_second - after_first
        assert increment > after_first * 0.5  # Resonance should amplify significantly

    def test_read_influences_energy(self):
        g = DynamicsGraph()
        g.add_node(_node("reader", energy=1.0))

        t = MemoryLandscapeTemplate()
        rng = np.random.default_rng(42)

        # Write strong memories, then read
        t.update(g, {
            "write_rate": 1.0,
            "read_rate": 0.5,
            "memory_persistence": 1.0,
            "retrieval_threshold": 0.0,
            "num_memory_slots": 4.0,
        }, rng)

        assert g.get_node("reader").state.energy > 1.0
