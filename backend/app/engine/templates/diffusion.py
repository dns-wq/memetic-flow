"""
Diffusion dynamics — information/idea spreading via edges.

Models how energy (representing idea adoption, information spread,
or viral content) propagates through the network along directed edges.

Update rule per node:
    energy += Σ(edge.transfer_rate × neighbor.energy × edge.weight) - energy × decay

Empirical priors from network science: cascade probability ~0.01–0.05
per edge per step (Watts 2002, Centola 2010).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class DiffusionTemplate(DynamicsTemplate):
    name = "diffusion"
    description = "Information/idea spreading via network edges"
    required_node_types = [NodeType.IDEA]
    required_edge_types = [EdgeType.INFORMATION]
    parameters = {
        "transfer_rate": ParameterSpec(0.03, 0.001, 0.5, "Probability of energy transfer per edge per step"),
        "decay_rate": ParameterSpec(0.01, 0.0, 0.2, "Fraction of energy lost per step"),
        "threshold": ParameterSpec(0.0, 0.0, 1.0, "Minimum energy required to transmit"),
        "noise_std": ParameterSpec(0.001, 0.0, 0.1, "Gaussian noise added to energy"),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        transfer = p["transfer_rate"]
        decay = p["decay_rate"]
        threshold = p["threshold"]
        noise_std = p["noise_std"]

        # Collect incoming energy deltas (read-then-write to avoid order dependence)
        deltas: dict[str, float] = {}

        for node_id, node in graph.nodes.items():
            incoming = 0.0
            for neighbor_id in graph.get_neighbors(node_id, "in"):
                nb = graph.get_node(neighbor_id)
                if nb.state.energy < threshold:
                    continue
                edges = graph.get_edges_between(neighbor_id, node_id)
                for edge in edges:
                    incoming += edge.transfer_rate * transfer * nb.state.energy * edge.weight

            loss = node.state.energy * decay
            noise = rng.normal(0, noise_std) if noise_std > 0 else 0.0
            deltas[node_id] = incoming - loss + noise

        # Apply deltas
        for node_id, delta in deltas.items():
            node = graph.get_node(node_id)
            node.state.energy = max(0.0, node.state.energy + delta)
