"""
Opinion dynamics — bounded-confidence belief updating.

Agents adjust their ideological_position toward neighbours whose
positions fall within a tolerance threshold.  Positions beyond
that threshold are ignored, which naturally produces polarization
and echo-chamber formation.

Based on the Hegselmann–Krause model (2002).
Empirical priors: tolerance ~0.2–0.4.
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class OpinionTemplate(DynamicsTemplate):
    name = "opinion"
    description = "Bounded-confidence opinion dynamics (Hegselmann–Krause)"
    required_node_types = [NodeType.AGENT]
    required_edge_types = [EdgeType.INFLUENCE]
    parameters = {
        "tolerance": ParameterSpec(0.3, 0.01, 1.0, "Max ideological distance for interaction"),
        "convergence_rate": ParameterSpec(0.1, 0.01, 1.0, "Speed of opinion adjustment per step"),
        "noise_std": ParameterSpec(0.01, 0.0, 0.2, "Random perturbation per dimension"),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        tolerance = p["tolerance"]
        convergence = p["convergence_rate"]
        noise_std = p["noise_std"]

        # Collect new positions (read-then-write)
        new_positions: dict[str, list[float]] = {}

        for node_id, node in graph.nodes.items():
            pos = node.state.ideological_position
            if not pos:
                continue

            pos_arr = np.array(pos, dtype=np.float64)
            influence_sum = np.zeros_like(pos_arr)
            weight_sum = 0.0

            for nb_id in graph.get_neighbors(node_id, "both"):
                nb = graph.get_node(nb_id)
                nb_pos = nb.state.ideological_position
                if not nb_pos or len(nb_pos) != len(pos):
                    continue

                nb_arr = np.array(nb_pos, dtype=np.float64)
                dist = float(np.linalg.norm(pos_arr - nb_arr))

                if dist <= tolerance:
                    # Weight by edge strength if available
                    edges = graph.get_edges_between(nb_id, node_id)
                    w = max((e.weight for e in edges), default=1.0)
                    influence_sum += w * (nb_arr - pos_arr)
                    weight_sum += w

            if weight_sum > 0:
                shift = convergence * influence_sum / weight_sum
                new_pos = pos_arr + shift
            else:
                new_pos = pos_arr

            # Add noise
            if noise_std > 0:
                new_pos += rng.normal(0, noise_std, size=new_pos.shape)

            new_positions[node_id] = new_pos.tolist()

        # Apply
        for node_id, new_pos in new_positions.items():
            graph.get_node(node_id).state.ideological_position = new_pos
