"""
Public Discourse mode.

Models democratic deliberation, electoral dynamics, coalition
formation, and policy feedback loops.
"""

from __future__ import annotations

from typing import Any

from ..dynamics import DynamicsGraph, NodeType
from .base import SimulationMode


class PublicDiscourseMode(SimulationMode):
    name = "public_discourse"
    description = (
        "Simulate polarization, coalition formation, and "
        "deliberation dynamics in public discourse."
    )
    icon = "megaphone"
    required_templates = ["opinion", "diffusion", "feedback"]
    optional_templates = [
        "evolutionary", "resource", "electoral", "coalition",
        "deliberation", "network_evolution",
    ]
    default_params = {
        "opinion": {
            "tolerance": 0.25,
            "convergence_rate": 0.12,
            "noise_std": 0.02,
        },
        "diffusion": {"transfer_rate": 0.05, "decay_rate": 0.005},
        "feedback": {"flow_coefficient": 0.1},
        "electoral": {"strategic_voting_rate": 0.1, "identity_weight": 0.3},
        "coalition": {"coalition_benefit_multiplier": 1.5, "defection_temptation": 0.3},
        "deliberation": {"evidence_weight": 0.5, "confirmation_bias": 0.3},
    }
    visualization_preset = "force"
    metrics_focus = [
        "polarization_index", "idea_entropy", "clustering_coefficient",
        "institutional_cohesion",
    ]
    suggested_for = [
        "politics", "election", "democracy", "debate",
        "polarization", "discourse", "coalition", "public opinion",
        "voting", "deliberation",
    ]

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        # Assign ideological positions to all agents
        for node in base_graph.nodes_by_type(NodeType.AGENT):
            if not node.state.ideological_position:
                h = hash(node.node_id)
                base_graph.update_node_state(
                    node.node_id,
                    ideological_position=[
                        ((h & 0xFF) / 255.0),
                        (((h >> 8) & 0xFF) / 255.0),
                    ],
                )
        # Ideas represent arguments/narratives with moderate energy
        for node in base_graph.nodes_by_type(NodeType.IDEA):
            base_graph.update_node_state(node.node_id, energy=2.0, stability=1.5)
        return base_graph

    def post_step_hook(
        self, graph: DynamicsGraph, timestep: int,
    ) -> list[dict[str, Any]]:
        """Detect polarization events and consensus formation."""
        events: list[dict[str, Any]] = []
        if timestep % 10 != 0:
            return events

        agents = graph.nodes_by_type(NodeType.AGENT)
        positions = [
            a.state.ideological_position[0]
            for a in agents
            if a.state.ideological_position
        ]
        if len(positions) < 4:
            return events

        mean = sum(positions) / len(positions)
        variance = sum((p - mean) ** 2 for p in positions) / len(positions)

        if variance > 0.08:
            events.append({
                "timestep": timestep,
                "event_type": "polarization_spike",
                "description": f"High polarization detected (variance={variance:.3f})",
                "data": {"variance": variance},
            })
        elif variance < 0.005:
            events.append({
                "timestep": timestep,
                "event_type": "consensus",
                "description": f"Consensus forming (variance={variance:.4f})",
                "data": {"variance": variance},
            })

        return events
