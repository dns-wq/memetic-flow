"""
Knowledge Ecosystems mode.

Models the production, validation, and propagation of knowledge —
scientific discovery, peer review, paradigm shifts, and
technology adoption.
"""

from __future__ import annotations

from typing import Any

from ..dynamics import DynamicsGraph, NodeType
from .base import SimulationMode


class KnowledgeEcosystemsMode(SimulationMode):
    name = "knowledge_ecosystems"
    description = (
        "Simulate knowledge production, paradigm dynamics, "
        "and innovation diffusion in research communities."
    )
    icon = "flask"
    required_templates = ["diffusion", "evolutionary", "resource"]
    optional_templates = [
        "feedback", "opinion", "knowledge_production", "peer_review",
        "paradigm", "memory_landscape",
    ]
    default_params = {
        "diffusion": {"transfer_rate": 0.04, "decay_rate": 0.005, "threshold": 0.1},
        "evolutionary": {
            "selection_strength": 0.08,
            "mutation_rate": 0.02,
            "carrying_capacity": 200.0,
        },
        "resource": {"growth_rate": 0.03, "flow_rate": 0.08},
        "knowledge_production": {"discovery_probability": 0.01, "collaboration_bonus": 0.1},
        "peer_review": {"reviewer_accuracy": 0.8, "replication_rate": 0.02},
        "paradigm": {"anomaly_accumulation_rate": 0.05, "crisis_threshold": 5.0},
    }
    visualization_preset = "force"
    metrics_focus = [
        "idea_entropy", "cascade_count", "clustering_coefficient",
        "total_energy",
    ]
    suggested_for = [
        "science", "research", "knowledge", "discovery",
        "innovation", "technology", "paradigm", "academic",
        "peer review", "R&D",
    ]

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        # Ideas represent knowledge claims — start with variable energy
        for i, node in enumerate(base_graph.nodes_by_type(NodeType.IDEA)):
            h = hash(node.node_id)
            energy = 1.0 + (h & 0xFF) / 128.0  # 1.0 - 3.0
            base_graph.update_node_state(
                node.node_id, energy=energy, mutation_rate=0.02,
            )
        # Agents (researchers) start with moderate influence
        for node in base_graph.nodes_by_type(NodeType.AGENT):
            base_graph.update_node_state(node.node_id, influence=0.8)
        return base_graph

    def post_step_hook(
        self, graph: DynamicsGraph, timestep: int,
    ) -> list[dict[str, Any]]:
        """Detect paradigm-shift-like events (dominant idea overtaken)."""
        events: list[dict[str, Any]] = []
        if timestep % 10 != 0:
            return events

        ideas = graph.nodes_by_type(NodeType.IDEA)
        if len(ideas) < 2:
            return events

        sorted_ideas = sorted(ideas, key=lambda n: n.state.energy, reverse=True)
        top = sorted_ideas[0]
        runner_up = sorted_ideas[1]

        if runner_up.state.energy > 0 and top.state.energy / runner_up.state.energy < 1.2:
            events.append({
                "timestep": timestep,
                "event_type": "paradigm_competition",
                "description": (
                    f"'{top.label}' and '{runner_up.label}' are closely competing "
                    f"(ratio={top.state.energy / runner_up.state.energy:.2f})"
                ),
                "data": {
                    "leader": top.node_id,
                    "challenger": runner_up.node_id,
                },
            })

        return events
