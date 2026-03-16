"""
Competitive dynamics — firm competition for market share.

Institution nodes compete for Resource nodes (market share).  Share
shifts based on relative quality, price, and network effects.  Includes
entry (new firms) and exit (failing firms) dynamics.

Priors from industrial organization (Jean Tirole, Michael Porter).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, GraphNode, NodeState, NodeType
from .base import DynamicsTemplate, ParameterSpec


class CompetitiveTemplate(DynamicsTemplate):
    name = "competitive"
    description = "Firm competition with market share, network effects, entry and exit"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "network_effect_strength": ParameterSpec(
            0.5, 0.0, 2.0,
            "Strength of winner-takes-most network effects",
        ),
        "entry_barrier": ParameterSpec(
            0.3, 0.0, 1.0,
            "Profit margin threshold for new firm entry",
        ),
        "exit_threshold": ParameterSpec(
            0.1, 0.0, 1.0,
            "Resource level below which a firm exits the market",
        ),
        "quality_weight": ParameterSpec(
            0.5, 0.0, 2.0,
            "Importance of quality (influence) in market share competition",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        net_effect = p["network_effect_strength"]
        entry_bar = p["entry_barrier"]
        exit_thresh = p["exit_threshold"]
        quality_w = p["quality_weight"]

        firms = list(graph.nodes_by_type(NodeType.INSTITUTION))
        if not firms:
            return

        # --- Bootstrap market share ---
        for firm in firms:
            if "market_share" not in firm.state.custom:
                firm.state.custom["market_share"] = 1.0 / len(firms)

        total_share = sum(f.state.custom.get("market_share", 0.0) for f in firms)
        if total_share < 1e-10:
            return

        # --- Phase 1: Compute competitive scores ---
        scores: dict[str, float] = {}
        for firm in firms:
            share = firm.state.custom.get("market_share", 0.0)
            quality = firm.state.influence * quality_w
            network = share ** net_effect  # Winner-takes-most
            score = quality + network + rng.normal(0, 0.02)
            scores[firm.node_id] = max(0.01, score)

        total_score = sum(scores.values())

        # --- Phase 2: Redistribute market share ---
        new_shares: dict[str, float] = {}
        for firm in firms:
            target_share = scores[firm.node_id] / total_score
            current = firm.state.custom.get("market_share", 0.0)
            # Smooth transition (20% per step toward target)
            new_share = current + 0.2 * (target_share - current)
            new_shares[firm.node_id] = max(0.0, new_share)

        # Normalize
        ns_total = sum(new_shares.values())
        if ns_total > 0:
            for firm in firms:
                firm.state.custom["market_share"] = (
                    new_shares[firm.node_id] / ns_total
                )
                # Market share → resources
                firm.state.resources += firm.state.custom["market_share"] * 0.5

        # --- Phase 3: Exit ---
        to_remove: list[str] = []
        for firm in firms:
            if firm.state.resources < exit_thresh:
                to_remove.append(firm.node_id)
                # Redistribute share
                freed = firm.state.custom.get("market_share", 0.0)
                surviving = [f for f in firms if f.node_id not in to_remove]
                if surviving:
                    per_firm = freed / len(surviving)
                    for s in surviving:
                        s.state.custom["market_share"] = (
                            s.state.custom.get("market_share", 0.0) + per_firm
                        )

        for nid in to_remove:
            graph.remove_node(nid)

        # --- Phase 4: Entry ---
        surviving_firms = list(graph.nodes_by_type(NodeType.INSTITUTION))
        if surviving_firms:
            avg_resources = sum(f.state.resources for f in surviving_firms) / len(surviving_firms)
            if avg_resources > entry_bar * 5 and rng.random() < 0.05:
                new_id = f"firm_{graph.timestep}_{rng.integers(1000)}"
                new_firm = GraphNode(
                    node_id=new_id,
                    node_type=NodeType.INSTITUTION,
                    label=f"NewFirm-{graph.timestep}",
                    state=NodeState(
                        resources=1.0, stability=0.5,
                        influence=float(rng.uniform(0.3, 0.8)),
                        energy=1.0,
                    ),
                )
                new_firm.state.custom["market_share"] = 0.01
                graph.add_node(new_firm)
