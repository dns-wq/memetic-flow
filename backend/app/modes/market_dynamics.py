"""
Market Dynamics mode.

Models economic systems — price formation, competitive dynamics,
supply chains, and market structure evolution.
"""

from __future__ import annotations

from typing import Any

from ..dynamics import DynamicsGraph, NodeType
from .base import SimulationMode


class MarketDynamicsMode(SimulationMode):
    name = "market_dynamics"
    description = (
        "Simulate competitive markets, supply chains, and "
        "economic dynamics with network-mediated resource flows."
    )
    icon = "chart"
    required_templates = ["resource", "diffusion", "feedback"]
    optional_templates = [
        "evolutionary", "opinion", "market_clearing", "competitive",
        "supply_chain", "network_evolution",
    ]
    default_params = {
        "resource": {
            "growth_rate": 0.04,
            "competition_coefficient": 0.03,
            "flow_rate": 0.15,
            "carrying_capacity": 20.0,
        },
        "diffusion": {"transfer_rate": 0.03, "decay_rate": 0.01},
        "feedback": {"flow_coefficient": 0.2, "saturation_limit": 40.0},
        "market_clearing": {"price_adjustment_speed": 0.1, "elasticity": 1.0},
        "competitive": {"network_effect_strength": 0.5, "quality_weight": 0.5},
        "supply_chain": {"flow_capacity": 1.0, "lead_time": 3.0},
    }
    visualization_preset = "force"
    metrics_focus = [
        "resource_gini", "total_energy", "cascade_count",
        "clustering_coefficient",
    ]
    suggested_for = [
        "market", "business", "competition", "supply chain",
        "trade", "pricing", "startup", "economy", "finance",
    ]

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        # Institutions (companies) get higher starting resources
        for node in base_graph.nodes_by_type(NodeType.INSTITUTION):
            base_graph.update_node_state(
                node.node_id, resources=8.0, energy=3.0, stability=2.0,
            )
        # Resource nodes get high capacity
        for node in base_graph.nodes_by_type(NodeType.RESOURCE):
            base_graph.update_node_state(
                node.node_id, resources=15.0, energy=5.0,
            )
        return base_graph

    def post_step_hook(
        self, graph: DynamicsGraph, timestep: int,
    ) -> list[dict[str, Any]]:
        """Detect market concentration and disruption events."""
        events: list[dict[str, Any]] = []
        if timestep % 10 != 0:
            return events

        institutions = graph.nodes_by_type(NodeType.INSTITUTION)
        if len(institutions) < 2:
            return events

        resources = [n.state.resources for n in institutions]
        total = sum(resources)
        if total == 0:
            return events

        for inst in institutions:
            share = inst.state.resources / total
            if share > 0.5:
                events.append({
                    "timestep": timestep,
                    "event_type": "market_concentration",
                    "description": (
                        f"'{inst.label}' dominates the market "
                        f"({share:.0%} of total resources)"
                    ),
                    "data": {"node_id": inst.node_id, "market_share": share},
                })

        return events
