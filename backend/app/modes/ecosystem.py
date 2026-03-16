"""
Digital Ecosystem of Minds mode.

Models cognition as an ecological process.  Cognitive agents behave like
species competing for resources (attention, memory).  Strategies evolve
through variation and selection — successful phenotypes reproduce,
failing ones go extinct.
"""

from __future__ import annotations

from typing import Any

from ..dynamics import DynamicsGraph, NodeType
from .base import SimulationMode

_EXTINCTION_THRESHOLD = 0.05
_REPRODUCTION_THRESHOLD = 8.0


class EcosystemMode(SimulationMode):
    name = "ecosystem"
    description = (
        "Model cognitive ecology — agents compete for attention, "
        "evolve strategies, and experience selection pressure."
    )
    icon = "brain"
    required_templates = ["evolutionary", "diffusion", "resource"]
    optional_templates = [
        "opinion", "feedback", "cognitive_ecology", "attention",
        "cognitive_types", "contagion", "game_theory",
    ]
    default_params = {
        "evolutionary": {
            "selection_strength": 0.15,
            "mutation_rate": 0.03,
            "carrying_capacity": 100.0,
        },
        "diffusion": {"transfer_rate": 0.05, "decay_rate": 0.02},
        "resource": {"growth_rate": 0.04, "competition_coefficient": 0.03},
        "cognitive_ecology": {"reproduction_threshold": 5.0, "extinction_threshold": 0.1},
        "attention": {"total_attention_pool": 100.0, "novelty_weight": 0.5},
        "cognitive_types": {"strategy_switch_probability": 0.05},
    }
    visualization_preset = "force"
    metrics_focus = [
        "idea_entropy", "resource_gini", "cascade_count", "total_energy",
    ]
    suggested_for = [
        "attention", "cognitive", "platform", "social media",
        "misinformation", "ecology", "strategy", "evolution",
    ]

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        # Boost mutation rate for agents to enable strategy evolution
        for node in base_graph.nodes_by_type(NodeType.AGENT):
            base_graph.update_node_state(node.node_id, mutation_rate=0.03)
        # Ideas start with higher energy to create initial competition
        for node in base_graph.nodes_by_type(NodeType.IDEA):
            base_graph.update_node_state(node.node_id, energy=3.0)
        return base_graph

    def post_step_hook(
        self, graph: DynamicsGraph, timestep: int
    ) -> list[dict[str, Any]]:
        """Detect extinction and reproduction events."""
        events: list[dict[str, Any]] = []

        if timestep % 5 != 0:
            return events

        agents = graph.nodes_by_type(NodeType.AGENT)

        for agent in agents:
            if agent.state.energy < _EXTINCTION_THRESHOLD:
                events.append({
                    "timestep": timestep,
                    "event_type": "extinction",
                    "description": f"{agent.label} went extinct (energy={agent.state.energy:.3f})",
                    "data": {"node_id": agent.node_id},
                })
            elif agent.state.energy > _REPRODUCTION_THRESHOLD:
                events.append({
                    "timestep": timestep,
                    "event_type": "reproduction",
                    "description": f"{agent.label} is thriving (energy={agent.state.energy:.2f})",
                    "data": {"node_id": agent.node_id},
                })

        return events
