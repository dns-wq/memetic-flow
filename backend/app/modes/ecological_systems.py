"""
Ecological Systems mode.

Models species interactions, habitat dynamics, ecosystem resilience,
and environmental policy impact using population ecology and
resource competition dynamics.
"""

from __future__ import annotations

from typing import Any

from ..dynamics import DynamicsGraph, NodeType
from .base import SimulationMode


class EcologicalSystemsMode(SimulationMode):
    name = "ecological_systems"
    description = (
        "Simulate species interactions, habitat dynamics, and "
        "ecosystem tipping points with ecological models."
    )
    icon = "leaf"
    required_templates = ["resource", "evolutionary", "feedback"]
    optional_templates = ["diffusion"]
    default_params = {
        "resource": {
            "growth_rate": 0.06,
            "competition_coefficient": 0.02,
            "flow_rate": 0.05,
            "carrying_capacity": 15.0,
        },
        "evolutionary": {
            "selection_strength": 0.1,
            "mutation_rate": 0.01,
            "carrying_capacity": 100.0,
        },
        "feedback": {"flow_coefficient": 0.08, "saturation_limit": 20.0},
    }
    visualization_preset = "force"
    metrics_focus = [
        "idea_entropy", "resource_gini", "total_energy",
        "feedback_loop_strength",
    ]
    suggested_for = [
        "ecology", "environment", "species", "habitat",
        "biodiversity", "conservation", "ecosystem",
        "sustainability", "climate", "wildlife",
    ]

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        # Resource nodes represent habitats — high stability
        for node in base_graph.nodes_by_type(NodeType.RESOURCE):
            base_graph.update_node_state(
                node.node_id, resources=12.0, stability=4.0, energy=5.0,
            )
        # Environment nodes represent landscape features
        for node in base_graph.nodes_by_type(NodeType.ENVIRONMENT):
            base_graph.update_node_state(
                node.node_id, stability=5.0, energy=3.0,
            )
        # Agents represent species populations
        for node in base_graph.nodes_by_type(NodeType.AGENT):
            h = hash(node.node_id)
            pop = 1.0 + (h & 0xFF) / 64.0  # 1.0 - 5.0
            base_graph.update_node_state(
                node.node_id, resources=pop, energy=pop, mutation_rate=0.01,
            )
        return base_graph

    def post_step_hook(
        self, graph: DynamicsGraph, timestep: int,
    ) -> list[dict[str, Any]]:
        """Detect ecosystem tipping points."""
        events: list[dict[str, Any]] = []
        if timestep % 10 != 0:
            return events

        # Check for resource collapse
        resources = graph.nodes_by_type(NodeType.RESOURCE)
        for res in resources:
            if res.state.resources < 1.0 and res.state.stability < 1.0:
                events.append({
                    "timestep": timestep,
                    "event_type": "habitat_collapse",
                    "description": (
                        f"'{res.label}' approaching collapse "
                        f"(resources={res.state.resources:.2f})"
                    ),
                    "data": {"node_id": res.node_id},
                })

        # Check for species at risk
        agents = graph.nodes_by_type(NodeType.AGENT)
        for agent in agents:
            if agent.state.energy < 0.1:
                events.append({
                    "timestep": timestep,
                    "event_type": "species_endangered",
                    "description": f"'{agent.label}' critically low (energy={agent.state.energy:.3f})",
                    "data": {"node_id": agent.node_id},
                })

        return events
