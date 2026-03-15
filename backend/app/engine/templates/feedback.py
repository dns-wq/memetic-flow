"""
Feedback systems — stocks-and-flows with circular causation.

Models system dynamics where nodes are "stocks" that accumulate or
deplete based on inflows and outflows defined by directed edges.
Supports saturation limits and delayed effects.

Based on system dynamics methodology (Forrester 1961, Sterman 2000).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class FeedbackTemplate(DynamicsTemplate):
    name = "feedback"
    description = "System dynamics: stocks, flows, and feedback loops"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "flow_coefficient": ParameterSpec(0.1, 0.0, 1.0, "Base flow rate multiplier"),
        "saturation_limit": ParameterSpec(50.0, 0.1, 10000.0, "Max stability/energy a node can hold"),
        "damping": ParameterSpec(0.01, 0.0, 0.2, "Natural decay/friction per step"),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        flow_coeff = p["flow_coefficient"]
        saturation = p["saturation_limit"]
        damping = p["damping"]

        # Compute inflows and outflows for stability (the "stock" variable)
        inflows: dict[str, float] = {nid: 0.0 for nid in graph.nodes}
        outflows: dict[str, float] = {nid: 0.0 for nid in graph.nodes}

        for edge in graph.edges.values():
            src = graph.get_node(edge.source_id)
            # Flow proportional to source stock, edge weight, and transfer rate
            amount = flow_coeff * edge.transfer_rate * src.state.stability * edge.weight

            # Saturation: reduce flow as target approaches limit
            tgt = graph.get_node(edge.target_id)
            saturation_factor = max(0.0, 1.0 - tgt.state.stability / saturation)
            amount *= saturation_factor

            outflows[edge.source_id] += amount
            inflows[edge.target_id] += amount

        # Apply stock updates
        for node_id, node in graph.nodes.items():
            net_flow = inflows[node_id] - outflows[node_id]
            decay = damping * node.state.stability
            node.state.stability = max(
                0.0,
                min(saturation, node.state.stability + net_flow - decay),
            )
