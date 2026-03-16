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
    # Phase 9
    InstitutionalTemplate,
    NormsTemplate,
    InnovationTemplate,
    # Phase 10
    CognitiveEcologyTemplate,
    AttentionTemplate,
    CognitiveTypesTemplate,
    # Phase 11
    MemeticFieldTemplate,
    MemeticEnergyTemplate,
    CulturalEvolutionTemplate,
    # Phase 12
    MarketClearingTemplate,
    CompetitiveTemplate,
    SupplyChainTemplate,
    # Phase 13
    ElectoralTemplate,
    CoalitionTemplate,
    DeliberationTemplate,
    # Phase 14
    KnowledgeProductionTemplate,
    PeerReviewTemplate,
    ParadigmTemplate,
    # Phase 15
    PopulationEcologyTemplate,
    HabitatTemplate,
    EcosystemServicesTemplate,
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
            # Phase 9
            "institutional", "norms", "innovation",
            # Phase 10
            "cognitive_ecology", "attention", "cognitive_types",
            # Phase 11
            "memetic_field", "memetic_energy", "cultural_evolution",
            # Phase 12
            "market_clearing", "competitive", "supply_chain",
            # Phase 13
            "electoral", "coalition", "deliberation",
            # Phase 14
            "knowledge_production", "peer_review", "paradigm",
            # Phase 15
            "population_ecology", "habitat", "ecosystem_services",
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


# ------------------------------------------------------------------
# Institutional template (Phase 9)
# ------------------------------------------------------------------

class TestInstitutional:
    def test_runs_and_updates_cooperation_scores(self):
        g = DynamicsGraph()
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0))
        g.add_node(_node("a2", NodeType.AGENT, energy=1.0))
        g.add_node(_node("a3", NodeType.AGENT, energy=1.0))
        g.add_node(_node("a4", NodeType.AGENT, energy=1.0))
        g.add_edge(_edge("e12", "a1", "a2", EdgeType.COOPERATION))
        g.add_edge(_edge("e13", "a1", "a3", EdgeType.COOPERATION))
        g.add_edge(_edge("e23", "a2", "a3", EdgeType.COOPERATION))
        g.add_edge(_edge("e34", "a3", "a4", EdgeType.COOPERATION))

        t = InstitutionalTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        # Cooperation scores should have been created
        a1 = g.get_node("a1")
        coop_keys = [k for k in a1.state.custom if k.startswith("coop_")]
        assert len(coop_keys) > 0

    def test_institution_forms_when_cooperation_high(self):
        g = DynamicsGraph()
        for i in range(4):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0))
        # Fully connect with cooperation edges
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(_edge(f"c{i}{j}", f"a{i}", f"a{j}", EdgeType.COOPERATION))
                g.add_edge(_edge(f"c{j}{i}", f"a{j}", f"a{i}", EdgeType.COOPERATION))

        t = InstitutionalTemplate()
        rng = np.random.default_rng(42)

        # Pre-set high cooperation scores so formation threshold is met
        for i in range(4):
            a = g.get_node(f"a{i}")
            for j in range(4):
                if i != j:
                    a.state.custom[f"coop_a{j}"] = 0.9

        t.update(g, {"formation_threshold": 0.6}, rng)

        # An institution should have been created
        institutions = list(g.nodes_by_type(NodeType.INSTITUTION))
        assert len(institutions) >= 1


# ------------------------------------------------------------------
# Norms template (Phase 9)
# ------------------------------------------------------------------

class TestNorms:
    def test_runs_without_error(self):
        g = DynamicsGraph()
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0))
        g.add_node(_node("a2", NodeType.AGENT, energy=1.0))
        norm = _node("norm1", NodeType.IDEA, stability=1.0)
        norm.state.custom["is_norm"] = 1.0
        g.add_node(norm)
        g.add_edge(_edge("e1", "a1", "norm1", EdgeType.INFORMATION))
        g.add_edge(_edge("e12", "a1", "a2", EdgeType.INFLUENCE))

        t = NormsTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)
        # Should not raise

    def test_norm_adoption_spreads(self):
        g = DynamicsGraph()
        # 4 agents fully connected; 3 already adopt the norm
        for i in range(4):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0))
        norm = _node("norm1", NodeType.IDEA, stability=1.0)
        norm.state.custom["is_norm"] = 1.0
        g.add_node(norm)
        # a0, a1, a2 adopt the norm (have INFORMATION edges)
        for i in range(3):
            g.add_edge(_edge(f"adopt{i}", f"a{i}", "norm1", EdgeType.INFORMATION))
        # Fully connect agents
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(_edge(f"e{i}{j}", f"a{i}", f"a{j}", EdgeType.INFLUENCE))
                g.add_edge(_edge(f"e{j}{i}", f"a{j}", f"a{i}", EdgeType.INFLUENCE))

        t = NormsTemplate()
        rng = np.random.default_rng(42)
        # Low threshold so a3 adopts (3/3 of its neighbours hold the norm)
        t.update(g, {"conformity_threshold": 0.5}, rng)

        # a3 should now have an edge to norm1
        edges_a3 = [e for e in g.edges.values() if e.source_id == "a3" and e.target_id == "norm1"]
        assert len(edges_a3) > 0


# ------------------------------------------------------------------
# Innovation template (Phase 9)
# ------------------------------------------------------------------

class TestInnovation:
    def test_runs_and_ages_innovations(self):
        g = DynamicsGraph()
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0, resources=1.0))
        idea = _node("idea1", NodeType.IDEA, energy=2.0)
        idea.state.custom["innovation_age"] = 5.0
        g.add_node(idea)
        g.add_edge(_edge("e1", "a1", "idea1", EdgeType.INFORMATION))

        t = InnovationTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        assert g.get_node("idea1").state.custom["innovation_age"] == 6.0

    def test_high_innovation_rate_creates_ideas(self):
        g = DynamicsGraph()
        for i in range(10):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0, resources=1.0))

        initial_ideas = len(list(g.nodes_by_type(NodeType.IDEA)))
        t = InnovationTemplate()
        rng = np.random.default_rng(42)
        # Very high innovation rate
        for _ in range(20):
            t.update(g, {"innovation_rate": 0.5}, rng)

        final_ideas = len(list(g.nodes_by_type(NodeType.IDEA)))
        assert final_ideas > initial_ideas


# ------------------------------------------------------------------
# Cognitive ecology template (Phase 10)
# ------------------------------------------------------------------

class TestCognitiveEcology:
    def test_phenotypes_initialized(self):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"a{i}", NodeType.AGENT, resources=2.0))
        for i in range(5):
            for j in range(i + 1, 5):
                g.add_edge(_edge(f"e{i}{j}", f"a{i}", f"a{j}", EdgeType.INFLUENCE))

        t = CognitiveEcologyTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        a0 = g.get_node("a0")
        assert "pheno_persuasion" in a0.state.custom
        assert "pheno_learning" in a0.state.custom

    def test_reproduction_when_resources_high(self):
        g = DynamicsGraph()
        g.add_node(_node("rich", NodeType.AGENT, resources=10.0, energy=1.0))
        g.add_node(_node("other", NodeType.AGENT, resources=1.0, energy=1.0))
        g.add_edge(_edge("e1", "rich", "other", EdgeType.INFLUENCE))

        t = CognitiveEcologyTemplate()
        rng = np.random.default_rng(42)

        initial_count = len(list(g.nodes_by_type(NodeType.AGENT)))
        t.update(g, {"reproduction_threshold": 5.0}, rng)

        final_count = len(list(g.nodes_by_type(NodeType.AGENT)))
        assert final_count > initial_count


# ------------------------------------------------------------------
# Attention template (Phase 10)
# ------------------------------------------------------------------

class TestAttention:
    def test_attention_distributed(self):
        g = DynamicsGraph()
        g.add_node(_node("i1", NodeType.IDEA, energy=5.0))
        g.add_node(_node("i2", NodeType.IDEA, energy=1.0))

        t = AttentionTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {"total_attention_pool": 100.0}, rng)

        i1 = g.get_node("i1")
        i2 = g.get_node("i2")
        assert "attention_share" in i1.state.custom
        assert "attention_share" in i2.state.custom
        # Higher energy idea should get more attention
        assert i1.state.custom["attention_share"] > i2.state.custom["attention_share"]

    def test_attention_age_increments(self):
        g = DynamicsGraph()
        g.add_node(_node("i1", NodeType.IDEA, energy=3.0))

        t = AttentionTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)
        t.update(g, {}, rng)

        assert g.get_node("i1").state.custom["attention_age"] == 2.0


# ------------------------------------------------------------------
# Cognitive types template (Phase 10)
# ------------------------------------------------------------------

class TestCognitiveTypes:
    def test_types_assigned(self):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0, ideological_position=[0.5, 0.5]))
        for i in range(5):
            for j in range(i + 1, 5):
                g.add_edge(_edge(f"e{i}{j}", f"a{i}", f"a{j}", EdgeType.INFLUENCE))

        t = CognitiveTypesTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        for i in range(5):
            a = g.get_node(f"a{i}")
            assert "cognitive_type" in a.state.custom
            assert int(a.state.custom["cognitive_type"]) in (0, 1, 2, 3)

    def test_positions_change(self):
        g = DynamicsGraph()
        g.add_node(_node("a0", NodeType.AGENT, energy=5.0, ideological_position=[0.2, 0.3]))
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0, ideological_position=[0.8, 0.7]))
        g.add_edge(_edge("e01", "a0", "a1", EdgeType.INFLUENCE))
        g.add_edge(_edge("e10", "a1", "a0", EdgeType.INFLUENCE))

        t = CognitiveTypesTemplate()
        rng = np.random.default_rng(42)

        orig_pos = list(g.get_node("a1").state.ideological_position)
        for _ in range(10):
            t.update(g, {}, rng)

        new_pos = g.get_node("a1").state.ideological_position
        assert orig_pos != new_pos


# ------------------------------------------------------------------
# Memetic field template (Phase 11)
# ------------------------------------------------------------------

class TestMemeticField:
    def test_agents_drift_toward_ideas(self):
        g = DynamicsGraph()
        g.add_node(_node("idea", NodeType.IDEA, energy=10.0, ideological_position=[0.8, 0.8]))
        g.add_node(_node("agent", NodeType.AGENT, energy=1.0, ideological_position=[0.2, 0.2]))

        t = MemeticFieldTemplate()
        rng = np.random.default_rng(42)

        orig_pos = list(g.get_node("agent").state.ideological_position)
        for _ in range(5):
            t.update(g, {"field_strength": 0.3, "conceptual_friction": 0.1}, rng)

        new_pos = g.get_node("agent").state.ideological_position
        # Agent should have drifted toward idea (0.8, 0.8)
        assert new_pos[0] > orig_pos[0]
        assert new_pos[1] > orig_pos[1]

    def test_gravity_well_detected(self):
        g = DynamicsGraph()
        g.add_node(_node("idea", NodeType.IDEA, energy=10.0, ideological_position=[0.5, 0.5]))
        # Place agents very close to the idea
        for i in range(3):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0,
                             ideological_position=[0.5 + i * 0.01, 0.5]))

        t = MemeticFieldTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {"field_strength": 0.1, "conceptual_friction": 0.5}, rng)

        assert g.get_node("idea").state.custom.get("gravity_well_size", 0) >= 1


# ------------------------------------------------------------------
# Memetic energy template (Phase 11)
# ------------------------------------------------------------------

class TestMemeticEnergy:
    def test_energy_approximately_conserved(self):
        g = DynamicsGraph()
        g.add_node(_node("i1", NodeType.IDEA, energy=30.0))
        g.add_node(_node("i2", NodeType.IDEA, energy=30.0))
        g.add_node(_node("i3", NodeType.IDEA, energy=40.0))

        t = MemeticEnergyTemplate()
        rng = np.random.default_rng(42)

        for _ in range(10):
            t.update(g, {"total_energy": 100.0, "injection_rate": 0.0, "dissipation_rate": 0.0}, rng)

        total = sum(g.get_node(f"i{i}").state.energy for i in range(1, 4))
        # Should stay near 100 with no injection/dissipation
        assert 80.0 < total < 120.0

    def test_high_fitness_gains_energy(self):
        g = DynamicsGraph()
        # i1 has many incoming edges (high fitness)
        g.add_node(_node("i1", NodeType.IDEA, energy=5.0))
        g.add_node(_node("i2", NodeType.IDEA, energy=5.0))
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0))
        g.add_node(_node("a2", NodeType.AGENT, energy=1.0))
        g.add_edge(_edge("e1", "a1", "i1", EdgeType.INFORMATION, weight=1.0))
        g.add_edge(_edge("e2", "a2", "i1", EdgeType.INFORMATION, weight=1.0))

        t = MemeticEnergyTemplate()
        rng = np.random.default_rng(42)

        e1_before = g.get_node("i1").state.energy
        for _ in range(10):
            t.update(g, {"total_energy": 100.0}, rng)

        # i1 should have gained relative to i2
        assert g.get_node("i1").state.energy > g.get_node("i2").state.energy


# ------------------------------------------------------------------
# Cultural evolution template (Phase 11)
# ------------------------------------------------------------------

class TestCulturalEvolution:
    def test_runs_without_error(self):
        g = DynamicsGraph()
        idea = _node("idea1", NodeType.IDEA, energy=2.0, ideological_position=[0.5, 0.5])
        g.add_node(idea)
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0))
        g.add_node(_node("a2", NodeType.AGENT, energy=1.0))
        g.add_edge(_edge("e1", "a1", "idea1", EdgeType.INFORMATION))
        g.add_edge(_edge("e12", "a1", "a2", EdgeType.INFLUENCE))

        t = CulturalEvolutionTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        # Should have bootstrapped transmissibility
        assert "transmissibility" in g.get_node("idea1").state.custom

    def test_mutations_create_new_ideas(self):
        g = DynamicsGraph()
        idea = _node("idea1", NodeType.IDEA, energy=2.0, ideological_position=[0.5, 0.5])
        g.add_node(idea)
        for i in range(5):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0))
            g.add_edge(_edge(f"ei{i}", f"a{i}", "idea1", EdgeType.INFORMATION))
        # Connect agents so they can transmit
        for i in range(5):
            for j in range(i + 1, 5):
                g.add_edge(_edge(f"e{i}{j}", f"a{i}", f"a{j}", EdgeType.INFLUENCE))

        t = CulturalEvolutionTemplate()
        rng = np.random.default_rng(42)

        initial_ideas = len(list(g.nodes_by_type(NodeType.IDEA)))
        for _ in range(50):
            t.update(g, {"mutation_rate": 0.5, "recombination_probability": 0.1}, rng)

        final_ideas = len(list(g.nodes_by_type(NodeType.IDEA)))
        assert final_ideas > initial_ideas


# ------------------------------------------------------------------
# Market clearing template (Phase 12)
# ------------------------------------------------------------------

class TestMarketClearing:
    def test_runs_and_sets_market_price(self):
        g = DynamicsGraph()
        for i in range(4):
            g.add_node(_node(f"a{i}", NodeType.AGENT, resources=5.0))

        t = MarketClearingTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        # Market price should have been set
        a0 = g.get_node("a0")
        assert "current_market_price" in a0.state.custom

    def test_transactions_transfer_resources(self):
        g = DynamicsGraph()
        # Create explicit buyer and seller
        buyer = _node("buyer", NodeType.AGENT, resources=10.0)
        seller = _node("seller", NodeType.AGENT, resources=5.0)
        g.add_node(buyer)
        g.add_node(seller)

        t = MarketClearingTemplate()
        rng = np.random.default_rng(42)

        # Force roles
        g.get_node("buyer").state.custom["is_seller"] = 0.0
        g.get_node("buyer").state.custom["reservation_price"] = 2.0
        g.get_node("buyer").state.custom["inventory"] = 0.0
        g.get_node("seller").state.custom["is_seller"] = 1.0
        g.get_node("seller").state.custom["reservation_price"] = 0.5
        g.get_node("seller").state.custom["inventory"] = 5.0
        g.get_node("buyer").state.custom["market_price"] = 1.0

        total_before = g.get_node("buyer").state.resources + g.get_node("seller").state.resources
        for _ in range(5):
            t.update(g, {"transaction_cost": 0.0}, rng)

        # Resources should have shifted (buyer spends, seller earns)
        buyer_r = g.get_node("buyer").state.resources
        seller_r = g.get_node("seller").state.resources
        # At least one of them should have changed
        assert buyer_r != 10.0 or seller_r != 5.0


# ------------------------------------------------------------------
# Competitive template (Phase 12)
# ------------------------------------------------------------------

class TestCompetitive:
    def test_market_share_initialized(self):
        g = DynamicsGraph()
        for i in range(3):
            g.add_node(_node(f"firm{i}", NodeType.INSTITUTION, resources=5.0, influence=1.0))

        t = CompetitiveTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        for i in range(3):
            firm = g.get_node(f"firm{i}")
            assert "market_share" in firm.state.custom

    def test_higher_quality_gains_share(self):
        g = DynamicsGraph()
        g.add_node(_node("strong", NodeType.INSTITUTION, resources=5.0, influence=3.0))
        g.add_node(_node("weak", NodeType.INSTITUTION, resources=5.0, influence=0.1))

        t = CompetitiveTemplate()
        rng = np.random.default_rng(42)

        for _ in range(20):
            t.update(g, {"quality_weight": 1.0}, rng)

        strong_share = g.get_node("strong").state.custom["market_share"]
        weak_share = g.get_node("weak").state.custom["market_share"]
        assert strong_share > weak_share


# ------------------------------------------------------------------
# Supply chain template (Phase 12)
# ------------------------------------------------------------------

class TestSupplyChain:
    def test_resources_flow_downstream(self):
        g = DynamicsGraph()
        g.add_node(_node("supplier", NodeType.RESOURCE, resources=10.0))
        g.add_node(_node("factory", NodeType.RESOURCE, resources=0.5))
        g.add_edge(_edge("flow1", "supplier", "factory", EdgeType.RESOURCE_FLOW, weight=1.0))

        t = SupplyChainTemplate()
        rng = np.random.default_rng(42)

        # Run enough steps for lead time to elapse and resources to arrive
        for _ in range(10):
            t.update(g, {"flow_capacity": 2.0, "lead_time": 1.0, "buffer_stock": 0.5}, rng)

        # Factory should have received some resources
        assert g.get_node("factory").state.resources > 0.5

    def test_disruption_reduces_flow(self):
        g = DynamicsGraph()
        g.add_node(_node("src", NodeType.RESOURCE, resources=20.0))
        g.add_node(_node("dst", NodeType.RESOURCE, resources=0.0))
        g.add_edge(_edge("flow", "src", "dst", EdgeType.RESOURCE_FLOW, weight=1.0))

        t = SupplyChainTemplate()
        rng = np.random.default_rng(42)

        # With very high disruption, less flow should arrive
        for _ in range(10):
            t.update(g, {
                "flow_capacity": 2.0, "lead_time": 0.0, "buffer_stock": 0.0,
                "disruption_probability": 0.0,
            }, rng)
        normal_flow = g.get_node("dst").state.resources

        # Reset
        g2 = DynamicsGraph()
        g2.add_node(_node("src", NodeType.RESOURCE, resources=20.0))
        g2.add_node(_node("dst", NodeType.RESOURCE, resources=0.0))
        g2.add_edge(_edge("flow", "src", "dst", EdgeType.RESOURCE_FLOW, weight=1.0))

        rng2 = np.random.default_rng(42)
        for _ in range(10):
            t.update(g2, {
                "flow_capacity": 2.0, "lead_time": 0.0, "buffer_stock": 0.0,
                "disruption_probability": 0.2,
            }, rng2)
        disrupted_flow = g2.get_node("dst").state.resources

        assert normal_flow >= disrupted_flow


# ------------------------------------------------------------------
# Electoral template (Phase 13)
# ------------------------------------------------------------------

class TestElectoral:
    def test_candidates_designated(self):
        g = DynamicsGraph()
        for i in range(10):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0,
                             influence=float(10 - i),
                             ideological_position=[i * 0.1, 0.5]))

        t = ElectoralTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        candidates = [a for a in g.nodes.values()
                      if a.state.custom.get("is_candidate", 0.0) >= 1.0]
        assert len(candidates) >= 2

    def test_election_produces_vote_shares(self):
        g = DynamicsGraph()
        # 2 candidates + 8 voters
        for i in range(10):
            g.add_node(_node(f"a{i}", NodeType.AGENT, energy=1.0,
                             influence=1.0,
                             ideological_position=[i * 0.1, 0.5]))
        g.get_node("a0").state.custom["is_candidate"] = 1.0
        g.get_node("a1").state.custom["is_candidate"] = 1.0

        t = ElectoralTemplate()
        rng = np.random.default_rng(42)
        # Advance timestep to election interval
        for _ in range(50):
            g.advance_timestep()
        t.update(g, {"election_interval": 50.0}, rng)

        # Candidates should have vote_share
        assert "vote_share" in g.get_node("a0").state.custom
        assert "vote_share" in g.get_node("a1").state.custom


# ------------------------------------------------------------------
# Coalition template (Phase 13)
# ------------------------------------------------------------------

class TestCoalition:
    def test_runs_and_initializes_ids(self):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"a{i}", NodeType.AGENT, resources=1.0,
                             ideological_position=[0.5, 0.5]))

        t = CoalitionTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        for i in range(5):
            assert "coalition_id" in g.get_node(f"a{i}").state.custom

    def test_proximate_agents_form_coalition(self):
        g = DynamicsGraph()
        # 5 agents all at the same position, should form a coalition
        for i in range(5):
            g.add_node(_node(f"a{i}", NodeType.AGENT, resources=1.0,
                             ideological_position=[0.5, 0.5]))

        t = CoalitionTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {"minimum_viable_size": 3.0}, rng)

        # At least 3 should share a coalition
        ids = [int(g.get_node(f"a{i}").state.custom.get("coalition_id", -1)) for i in range(5)]
        from collections import Counter
        counts = Counter(i for i in ids if i >= 0)
        assert any(c >= 3 for c in counts.values())


# ------------------------------------------------------------------
# Deliberation template (Phase 13)
# ------------------------------------------------------------------

class TestDeliberation:
    def test_runs_and_shifts_positions(self):
        g = DynamicsGraph()
        g.add_node(_node("a0", NodeType.AGENT, energy=1.0, ideological_position=[0.2, 0.3]))
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0, ideological_position=[0.8, 0.7]))
        g.add_edge(_edge("e01", "a0", "a1", EdgeType.INFLUENCE))
        g.add_edge(_edge("e10", "a1", "a0", EdgeType.INFLUENCE))

        t = DeliberationTemplate()
        rng = np.random.default_rng(42)

        orig_a0 = list(g.get_node("a0").state.ideological_position)
        for _ in range(10):
            t.update(g, {"confirmation_bias": 0.0, "engagement_selectivity": 0.0}, rng)

        new_a0 = g.get_node("a0").state.ideological_position
        # Positions should have shifted toward each other
        assert new_a0[0] > orig_a0[0]

    def test_high_confirmation_bias_limits_convergence(self):
        g = DynamicsGraph()
        g.add_node(_node("a0", NodeType.AGENT, energy=1.0, ideological_position=[0.1, 0.1]))
        g.add_node(_node("a1", NodeType.AGENT, energy=1.0, ideological_position=[0.9, 0.9]))
        g.add_edge(_edge("e01", "a0", "a1", EdgeType.INFLUENCE))
        g.add_edge(_edge("e10", "a1", "a0", EdgeType.INFLUENCE))

        t = DeliberationTemplate()

        # Low bias run
        g_low = DynamicsGraph()
        g_low.add_node(_node("a0", NodeType.AGENT, energy=1.0, ideological_position=[0.1, 0.1]))
        g_low.add_node(_node("a1", NodeType.AGENT, energy=1.0, ideological_position=[0.9, 0.9]))
        g_low.add_edge(_edge("e01", "a0", "a1", EdgeType.INFLUENCE))
        g_low.add_edge(_edge("e10", "a1", "a0", EdgeType.INFLUENCE))

        rng_low = np.random.default_rng(42)
        for _ in range(20):
            t.update(g_low, {"confirmation_bias": 0.0, "engagement_selectivity": 0.0}, rng_low)

        # High bias run
        g_high = DynamicsGraph()
        g_high.add_node(_node("a0", NodeType.AGENT, energy=1.0, ideological_position=[0.1, 0.1]))
        g_high.add_node(_node("a1", NodeType.AGENT, energy=1.0, ideological_position=[0.9, 0.9]))
        g_high.add_edge(_edge("e01", "a0", "a1", EdgeType.INFLUENCE))
        g_high.add_edge(_edge("e10", "a1", "a0", EdgeType.INFLUENCE))

        rng_high = np.random.default_rng(42)
        for _ in range(20):
            t.update(g_high, {"confirmation_bias": 0.9, "engagement_selectivity": 0.0}, rng_high)

        # Convergence should be greater with low bias
        low_dist = abs(
            g_low.get_node("a0").state.ideological_position[0]
            - g_low.get_node("a1").state.ideological_position[0]
        )
        high_dist = abs(
            g_high.get_node("a0").state.ideological_position[0]
            - g_high.get_node("a1").state.ideological_position[0]
        )
        assert low_dist <= high_dist


# ------------------------------------------------------------------
# Knowledge production template (Phase 14)
# ------------------------------------------------------------------

class TestKnowledgeProduction:
    def test_runs_and_bootstraps_skill(self):
        g = DynamicsGraph()
        g.add_node(_node("r1", NodeType.AGENT, energy=1.0))
        g.add_node(_node("r2", NodeType.AGENT, energy=1.0))
        g.add_edge(_edge("e12", "r1", "r2", EdgeType.COOPERATION))

        t = KnowledgeProductionTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        assert "researcher_skill" in g.get_node("r1").state.custom

    def test_high_discovery_rate_creates_ideas(self):
        g = DynamicsGraph()
        for i in range(5):
            g.add_node(_node(f"r{i}", NodeType.AGENT, energy=1.0))
        # Give them prerequisite ideas
        for i in range(5):
            for j in range(3):
                idea_id = f"prereq_{i}_{j}"
                g.add_node(_node(idea_id, NodeType.IDEA, energy=1.0))
                g.add_edge(_edge(f"ep{i}{j}", f"r{i}", idea_id, EdgeType.INFORMATION))
        # Connect researchers for collaboration
        for i in range(5):
            for j in range(i + 1, 5):
                g.add_edge(_edge(f"c{i}{j}", f"r{i}", f"r{j}", EdgeType.COOPERATION))

        t = KnowledgeProductionTemplate()
        rng = np.random.default_rng(42)

        initial_ideas = len(list(g.nodes_by_type(NodeType.IDEA)))
        for _ in range(20):
            t.update(g, {"discovery_probability": 0.5, "prerequisite_depth": 2.0}, rng)

        final_ideas = len(list(g.nodes_by_type(NodeType.IDEA)))
        assert final_ideas > initial_ideas


# ------------------------------------------------------------------
# Peer review template (Phase 14)
# ------------------------------------------------------------------

class TestPeerReview:
    def test_runs_and_sets_review_status(self):
        g = DynamicsGraph()
        idea = _node("paper1", NodeType.IDEA, energy=2.0)
        idea.state.custom["citation_count"] = 0.0
        idea.state.custom["evidence_strength"] = 0.8
        g.add_node(idea)

        t = PeerReviewTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        assert "review_status" in g.get_node("paper1").state.custom

    def test_high_evidence_accepted(self):
        g = DynamicsGraph()
        idea = _node("good_paper", NodeType.IDEA, energy=1.0)
        idea.state.custom["citation_count"] = 0.0
        idea.state.custom["evidence_strength"] = 0.95
        g.add_node(idea)

        t = PeerReviewTemplate()
        rng = np.random.default_rng(42)
        # High accuracy reviewer should accept high-evidence paper
        t.update(g, {"reviewer_accuracy": 0.99}, rng)

        status = g.get_node("good_paper").state.custom["review_status"]
        assert status == 1.0  # _ACCEPTED


# ------------------------------------------------------------------
# Paradigm template (Phase 14)
# ------------------------------------------------------------------

class TestParadigm:
    def test_runs_and_bootstraps_anomalies(self):
        g = DynamicsGraph()
        par = _node("par1", NodeType.INSTITUTION, energy=5.0, stability=3.0)
        g.add_node(par)

        t = ParadigmTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        assert "anomaly_count" in g.get_node("par1").state.custom
        assert "is_paradigm" in g.get_node("par1").state.custom

    def test_normal_science_boosts_members(self):
        g = DynamicsGraph()
        par = _node("paradigm1", NodeType.INSTITUTION, energy=5.0, stability=3.0)
        par.state.custom["is_paradigm"] = 1.0
        par.state.custom["anomaly_count"] = 0.0
        g.add_node(par)

        agent = _node("scientist", NodeType.AGENT, energy=1.0)
        g.add_node(agent)
        g.assign_institution("scientist", "paradigm1")
        g.add_edge(_edge("mem1", "scientist", "paradigm1", EdgeType.MEMBERSHIP, weight=1.0))

        t = ParadigmTemplate()
        rng = np.random.default_rng(42)

        energy_before = g.get_node("scientist").state.energy
        for _ in range(10):
            t.update(g, {}, rng)

        assert g.get_node("scientist").state.energy > energy_before


# ------------------------------------------------------------------
# Population ecology template (Phase 15)
# ------------------------------------------------------------------

class TestPopulationEcology:
    def test_population_grows_logistically(self):
        g = DynamicsGraph()
        g.add_node(_node("species1", NodeType.RESOURCE, resources=1.0))

        t = PopulationEcologyTemplate()
        rng = np.random.default_rng(42)

        for _ in range(50):
            t.update(g, {"birth_rate": 0.2, "death_rate": 0.05, "carrying_capacity": 100.0}, rng)

        pop = g.get_node("species1").state.custom["population"]
        assert pop > 10.0  # Should have grown from initial ~10
        assert pop <= 200.0  # Hard cap at 2x carrying capacity

    def test_predation_reduces_prey(self):
        g = DynamicsGraph()
        g.add_node(_node("predator", NodeType.AGENT, resources=5.0))
        g.add_node(_node("prey", NodeType.RESOURCE, resources=5.0))
        # Single directional edge: predator → prey (predator hunts prey)
        g.add_edge(_edge("hunt", "predator", "prey", EdgeType.CONFLICT))

        t = PopulationEcologyTemplate()
        rng = np.random.default_rng(42)

        # Bootstrap populations
        t.update(g, {"predation_rate": 0.0}, rng)
        prey_pop_before = g.get_node("prey").state.custom["population"]

        for _ in range(10):
            t.update(g, {"predation_rate": 0.1, "birth_rate": 0.0, "death_rate": 0.0}, rng)

        prey_pop_after = g.get_node("prey").state.custom["population"]
        assert prey_pop_after < prey_pop_before


# ------------------------------------------------------------------
# Habitat template (Phase 15)
# ------------------------------------------------------------------

class TestHabitat:
    def test_runs_and_bootstraps_quality(self):
        g = DynamicsGraph()
        g.add_node(_node("forest", NodeType.ENVIRONMENT, energy=1.0))

        t = HabitatTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        assert "habitat_quality" in g.get_node("forest").state.custom
        assert "habitat_area" in g.get_node("forest").state.custom

    def test_degradation_from_occupant_pressure(self):
        g = DynamicsGraph()
        habitat = _node("meadow", NodeType.ENVIRONMENT, energy=3.0)
        g.add_node(habitat)
        # Many occupants creating pressure
        for i in range(10):
            occupant = _node(f"species{i}", NodeType.AGENT, resources=5.0)
            occupant.state.custom["population"] = 50.0
            g.add_node(occupant)
            g.add_edge(_edge(f"occ{i}", f"species{i}", "meadow", EdgeType.RESOURCE_FLOW))

        t = HabitatTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {"degradation_rate": 0.1, "restoration_rate": 0.0}, rng)

        quality = g.get_node("meadow").state.custom["habitat_quality"]
        assert quality < 0.8  # Should have degraded from default 0.8


# ------------------------------------------------------------------
# Ecosystem services template (Phase 15)
# ------------------------------------------------------------------

class TestEcosystemServices:
    def test_runs_and_computes_service_value(self):
        g = DynamicsGraph()
        habitat = _node("reef", NodeType.ENVIRONMENT, energy=3.0)
        habitat.state.custom["habitat_quality"] = 0.9
        g.add_node(habitat)

        # Add some species with populations
        for i in range(3):
            sp = _node(f"sp{i}", NodeType.RESOURCE, resources=5.0)
            sp.state.custom["population"] = 10.0
            g.add_node(sp)
            g.add_edge(_edge(f"lives{i}", f"sp{i}", "reef", EdgeType.RESOURCE_FLOW))

        t = EcosystemServicesTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {}, rng)

        assert "service_value" in g.get_node("reef").state.custom
        assert g.get_node("reef").state.custom["service_value"] > 0.0

    def test_low_biodiversity_collapses_services(self):
        g = DynamicsGraph()
        habitat = _node("degraded", NodeType.ENVIRONMENT, energy=3.0)
        habitat.state.custom["habitat_quality"] = 0.9
        g.add_node(habitat)

        # Species with zero population (extinct)
        for i in range(5):
            sp = _node(f"sp{i}", NodeType.RESOURCE, resources=0.0)
            sp.state.custom["population"] = 0.0  # Extinct
            g.add_node(sp)
            g.add_edge(_edge(f"lives{i}", f"sp{i}", "degraded", EdgeType.RESOURCE_FLOW))

        t = EcosystemServicesTemplate()
        rng = np.random.default_rng(42)
        t.update(g, {"biodiversity_threshold": 0.3}, rng)

        # Service multiplier should be low when all species are extinct
        multiplier = g.get_node("degraded").state.custom.get("service_multiplier", 1.0)
        assert multiplier < 0.5
