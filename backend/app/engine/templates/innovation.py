"""
Technology / innovation diffusion — stochastic invention and S-curve adoption.

Agents can invent new IDEA nodes (innovations).  Innovations provide
resource bonuses to adopters following an S-curve pattern (slow start →
rapid spread → saturation).  Old innovations become obsolete and decay.

Priors from innovation diffusion theory (Everett Rogers, Bass model).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, GraphNode, NodeState, NodeType
from .base import DynamicsTemplate, ParameterSpec


def _sigmoid(x: float) -> float:
    """Standard sigmoid, clamped to avoid overflow."""
    return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, x))))


class InnovationTemplate(DynamicsTemplate):
    name = "innovation"
    description = "Stochastic invention creation with S-curve adoption diffusion"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "innovation_rate": ParameterSpec(
            0.005, 0.0, 0.1,
            "Per-agent probability of inventing a new idea per step",
        ),
        "adoption_advantage": ParameterSpec(
            0.2, 0.0, 2.0,
            "Resource bonus per step for adopters of an innovation",
        ),
        "obsolescence_rate": ParameterSpec(
            0.01, 0.0, 0.1,
            "Rate at which old innovations lose energy",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        innov_rate = p["innovation_rate"]
        advantage = p["adoption_advantage"]
        obsol_rate = p["obsolescence_rate"]

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        ideas = list(graph.nodes_by_type(NodeType.IDEA))

        # --- Phase 1: Age existing innovations ---
        for idea in ideas:
            age = idea.state.custom.get("innovation_age", -1.0)
            if age >= 0.0:
                idea.state.custom["innovation_age"] = age + 1.0

        # --- Phase 2: Invention — agents may create new ideas ---
        new_ideas: list[tuple[str, GraphNode]] = []  # (creator_id, idea_node)
        for agent in agents:
            if rng.random() < innov_rate:
                idea_id = f"innov_{graph.timestep}_{agent.node_id[:8]}_{rng.integers(100000)}"
                idea_node = GraphNode(
                    node_id=idea_id,
                    node_type=NodeType.IDEA,
                    label=f"Innovation-{graph.timestep}",
                    state=NodeState(energy=1.5, stability=0.5, mutation_rate=0.02),
                    metadata={"creator": agent.node_id},
                )
                idea_node.state.custom["innovation_age"] = 0.0
                new_ideas.append((agent.node_id, idea_node))

        for creator_id, idea_node in new_ideas:
            graph.add_node(idea_node)
            graph.add_edge(GraphEdge(
                edge_id=f"created_{creator_id}_{idea_node.node_id}",
                source_id=creator_id, target_id=idea_node.node_id,
                edge_type=EdgeType.INFORMATION, weight=1.0,
            ))

        # --- Phase 3: S-curve adoption benefit ---
        # Adopters = agents connected to an innovation via INFORMATION edges
        for idea in list(graph.nodes_by_type(NodeType.IDEA)):
            age = idea.state.custom.get("innovation_age", -1.0)
            if age < 0.0:
                continue  # Not an innovation
            # S-curve: benefit peaks around age=30, ramps up slowly, plateaus
            s_factor = _sigmoid((age - 30.0) / 10.0)
            benefit = advantage * s_factor

            # Find adopters (agents with INFORMATION edge to this idea)
            for nb_id in graph.get_neighbors(idea.node_id, "in"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type == NodeType.AGENT:
                    nb.state.resources = max(0.0, nb.state.resources + benefit)

        # --- Phase 4: Obsolescence ---
        for idea in list(graph.nodes_by_type(NodeType.IDEA)):
            age = idea.state.custom.get("innovation_age", -1.0)
            if age > 50.0:
                idea.state.energy = max(0.0, idea.state.energy * (1.0 - obsol_rate))
