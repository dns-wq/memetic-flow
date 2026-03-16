"""
Memetic Physics mode.

Treats ideas as particles obeying dynamics analogous to physics.
Measures "force", "mass", and "entropy" of memes as they propagate
through conceptual fields.  Ideological gravity wells form where
agents cluster around high-energy ideas.
"""

from __future__ import annotations

from typing import Any

from ..dynamics import DynamicsGraph, NodeType
from .base import SimulationMode


class MemeticPhysicsMode(SimulationMode):
    name = "memetic_physics"
    description = (
        "Treat ideas as particles in a conceptual field — "
        "measure memetic energy, entropy, and gravity wells."
    )
    icon = "atom"
    required_templates = ["diffusion", "evolutionary", "feedback"]
    optional_templates = [
        "opinion", "resource", "memetic_field", "memetic_energy",
        "cultural_evolution", "memory_landscape",
    ]
    default_params = {
        "diffusion": {"transfer_rate": 0.06, "decay_rate": 0.008, "noise_std": 0.005},
        "evolutionary": {
            "selection_strength": 0.12,
            "mutation_rate": 0.04,
            "carrying_capacity": 150.0,
        },
        "feedback": {"flow_coefficient": 0.15, "saturation_limit": 30.0},
        "memetic_field": {"field_strength": 0.1, "conceptual_friction": 0.3},
        "memetic_energy": {"total_energy": 100.0, "transfer_efficiency": 0.8},
        "cultural_evolution": {"mutation_rate": 0.02, "recombination_probability": 0.01},
    }
    visualization_preset = "field"
    metrics_focus = [
        "idea_entropy", "total_energy", "cascade_count",
        "feedback_loop_strength",
    ]
    suggested_for = [
        "narrative", "meme", "culture", "propaganda",
        "campaign", "ideology", "discourse", "media",
    ]

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        # Give ideas a 2D conceptual position from their node_id hash
        for node in base_graph.nodes_by_type(NodeType.IDEA):
            h = hash(node.node_id)
            base_graph.update_node_state(
                node.node_id,
                ideological_position=[
                    ((h & 0xFF) / 255.0),
                    (((h >> 8) & 0xFF) / 255.0),
                ],
                energy=2.0,
                mutation_rate=0.05,
            )
        # Agents positioned by their opinion vector (already set or default)
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
        return base_graph

    def post_step_hook(
        self, graph: DynamicsGraph, timestep: int
    ) -> list[dict[str, Any]]:
        """Detect energy concentration events (gravity well formation)."""
        events: list[dict[str, Any]] = []

        if timestep % 10 != 0:
            return events

        ideas = graph.nodes_by_type(NodeType.IDEA)
        if not ideas:
            return events

        energies = [n.state.energy for n in ideas]
        total = sum(energies)
        if total == 0:
            return events

        for idea in ideas:
            share = idea.state.energy / total
            if share > 0.4:
                events.append({
                    "timestep": timestep,
                    "event_type": "gravity_well",
                    "description": (
                        f"'{idea.label}' dominates the memetic field "
                        f"({share:.0%} of total energy)"
                    ),
                    "data": {"node_id": idea.node_id, "energy_share": share},
                })

        return events
