"""
Resource flow — Lotka-Volterra inspired competition and predation.

Models resource dynamics where nodes grow logistically and compete
or flow resources along directed edges.  Supports predator-prey-like
dynamics and resource competition between agents/institutions.

Based on Lotka-Volterra competition equations from ecological modeling.
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class ResourceTemplate(DynamicsTemplate):
    name = "resource"
    description = "Lotka-Volterra resource competition and flow dynamics"
    required_node_types = [NodeType.RESOURCE]
    required_edge_types = [EdgeType.RESOURCE_FLOW]
    parameters = {
        "growth_rate": ParameterSpec(0.05, 0.0, 0.5, "Intrinsic growth rate per step"),
        "competition_coefficient": ParameterSpec(0.01, 0.0, 0.1, "Strength of resource competition between nodes"),
        "flow_rate": ParameterSpec(0.1, 0.0, 1.0, "Fraction of resources flowing along edges per step"),
        "carrying_capacity": ParameterSpec(10.0, 0.1, 1000.0, "Per-node resource cap"),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        growth = p["growth_rate"]
        competition = p["competition_coefficient"]
        flow = p["flow_rate"]
        capacity = p["carrying_capacity"]

        # Phase 1: logistic growth + competition
        deltas: dict[str, float] = {}

        for node_id, node in graph.nodes.items():
            r = node.state.resources

            # Logistic growth: r' = growth * r * (1 - r/K)
            logistic = growth * r * (1.0 - r / capacity)

            # Competition: reduce growth proportional to neighbours' resources
            comp_loss = 0.0
            for nb_id in graph.get_neighbors(node_id, "both"):
                nb = graph.get_node(nb_id)
                comp_loss += competition * r * nb.state.resources / capacity

            deltas[node_id] = logistic - comp_loss

        # Phase 2: resource flow along RESOURCE_FLOW edges
        flow_deltas: dict[str, float] = {nid: 0.0 for nid in graph.nodes}

        for edge in graph.edges_by_type(EdgeType.RESOURCE_FLOW):
            src = graph.get_node(edge.source_id)
            amount = flow * edge.transfer_rate * src.state.resources * edge.weight
            flow_deltas[edge.source_id] -= amount
            flow_deltas[edge.target_id] += amount

        # Apply both
        for node_id in graph.nodes:
            node = graph.get_node(node_id)
            total_delta = deltas.get(node_id, 0.0) + flow_deltas.get(node_id, 0.0)
            node.state.resources = max(0.0, min(capacity, node.state.resources + total_delta))
