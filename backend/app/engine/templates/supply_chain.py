"""
Supply chain flow — multi-tier production networks with disruptions.

Directed RESOURCE_FLOW edges represent supply links with capacity
constraints and lead times.  Resources flow downstream.  Disruptions
propagate upstream (bullwhip effect).

Priors from operations research (Hau Lee bullwhip effect, supply chain
network design).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class SupplyChainTemplate(DynamicsTemplate):
    name = "supply_chain"
    description = "Multi-tier supply chain flow with capacity constraints and disruptions"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "flow_capacity": ParameterSpec(
            1.0, 0.1, 10.0,
            "Maximum flow per edge per step",
        ),
        "lead_time": ParameterSpec(
            3.0, 0.0, 20.0,
            "Steps of delay before flow arrives at destination",
        ),
        "buffer_stock": ParameterSpec(
            0.5, 0.0, 5.0,
            "Buffer inventory that absorbs demand spikes",
        ),
        "disruption_probability": ParameterSpec(
            0.01, 0.0, 0.2,
            "Probability per edge per step of a supply disruption",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        capacity = p["flow_capacity"]
        lead_time = p["lead_time"]
        buffer = p["buffer_stock"]
        disruption_p = p["disruption_probability"]

        # Get all RESOURCE_FLOW edges
        flow_edges = [
            e for e in graph.edges.values()
            if e.edge_type == EdgeType.RESOURCE_FLOW
        ]
        if not flow_edges:
            return

        # --- Bootstrap edge state ---
        for edge in flow_edges:
            if "sc_pipeline" not in edge.metadata:
                edge.metadata["sc_pipeline"] = []  # Queued flow amounts
            if "sc_disrupted" not in edge.metadata:
                edge.metadata["sc_disrupted"] = False

        # --- Phase 1: Disruptions ---
        for edge in flow_edges:
            if rng.random() < disruption_p:
                edge.metadata["sc_disrupted"] = True
                edge.weight *= 0.5  # Halve capacity
            elif edge.metadata.get("sc_disrupted", False):
                # Recovery (10% chance per step)
                if rng.random() < 0.1:
                    edge.metadata["sc_disrupted"] = False
                    edge.weight = min(1.0, edge.weight * 1.5)

        # --- Phase 2: Flow through edges ---
        resource_deltas: dict[str, float] = {}

        for edge in flow_edges:
            src = graph.get_node(edge.source_id)
            tgt = graph.get_node(edge.target_id)
            if src is None or tgt is None:
                continue

            # Available supply from source (minus buffer)
            available = max(0.0, src.state.resources - buffer)
            # Effective capacity (reduced if disrupted)
            eff_capacity = capacity * edge.weight
            # Demand signal from target (how much they need)
            target_deficit = max(0.0, 2.0 - tgt.state.resources)

            flow = min(available, eff_capacity, target_deficit)
            if flow <= 0:
                continue

            # Add to pipeline with lead time
            pipeline = edge.metadata.get("sc_pipeline", [])
            pipeline.append({"amount": flow, "remaining": int(lead_time)})
            edge.metadata["sc_pipeline"] = pipeline

            # Deduct from source immediately
            resource_deltas[src.node_id] = (
                resource_deltas.get(src.node_id, 0.0) - flow
            )

        # --- Phase 3: Advance pipeline ---
        for edge in flow_edges:
            tgt = graph.get_node(edge.target_id)
            if tgt is None:
                continue

            pipeline = edge.metadata.get("sc_pipeline", [])
            new_pipeline = []
            for item in pipeline:
                remaining = item.get("remaining", 0) - 1
                if remaining <= 0:
                    # Deliver to target
                    resource_deltas[tgt.node_id] = (
                        resource_deltas.get(tgt.node_id, 0.0)
                        + item.get("amount", 0.0)
                    )
                else:
                    new_pipeline.append(
                        {"amount": item["amount"], "remaining": remaining}
                    )
            edge.metadata["sc_pipeline"] = new_pipeline

        # --- Apply deltas ---
        for node_id, delta in resource_deltas.items():
            node = graph.get_node(node_id)
            if node is not None:
                node.state.resources = max(0.0, node.state.resources + delta)

        # --- Bullwhip: upstream nodes amplify perceived demand ---
        for edge in flow_edges:
            src = graph.get_node(edge.source_id)
            tgt = graph.get_node(edge.target_id)
            if src is None or tgt is None:
                continue
            # If target is depleting, signal amplified demand upstream
            if tgt.state.resources < 1.0:
                amplification = 1.5 * (1.0 - tgt.state.resources)
                src.state.custom["demand_signal"] = (
                    src.state.custom.get("demand_signal", 1.0) + amplification
                )
