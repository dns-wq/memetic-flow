"""
Norm formation dynamics — conformity-driven adoption of shared rules.

Norms are represented as IDEA nodes with ``custom["is_norm"] = 1.0``.
Agents adopt norms when a critical fraction of their neighbours already
hold them.  Adopted norms gain stability; violators lose energy.

Priors from social norm theory (Cristina Bicchieri, Robert Boyd).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, NodeType
from .base import DynamicsTemplate, ParameterSpec


class NormsTemplate(DynamicsTemplate):
    name = "norms"
    description = "Conformity-driven norm adoption among agents"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "conformity_threshold": ParameterSpec(
            0.5, 0.1, 1.0,
            "Fraction of neighbours that must hold a norm before an agent adopts it",
        ),
        "norm_stability_bonus": ParameterSpec(
            0.1, 0.0, 1.0,
            "Stability increase per step for widely-adopted norms",
        ),
        "violation_penalty": ParameterSpec(
            0.05, 0.0, 0.5,
            "Energy penalty for agents holding ideas that conflict with adopted norms",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        threshold = p["conformity_threshold"]
        bonus = p["norm_stability_bonus"]
        penalty = p["violation_penalty"]

        # Identify norm ideas
        norms = [
            n for n in graph.nodes_by_type(NodeType.IDEA)
            if n.state.custom.get("is_norm", 0.0) >= 1.0
        ]
        if not norms:
            return

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not agents:
            return

        # Build set of (agent_id, norm_id) adoptions
        adoptions: set[tuple[str, str]] = set()
        for agent in agents:
            for nb_id in graph.get_neighbors(agent.node_id, "out"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.state.custom.get("is_norm", 0.0) >= 1.0:
                    adoptions.add((agent.node_id, nb_id))

        # Collect new adoptions (read-then-write)
        new_adoptions: list[tuple[str, str]] = []

        for norm in norms:
            norm_id = norm.node_id
            # Count how many agents hold this norm
            adopters = {aid for aid, nid in adoptions if nid == norm_id}

            for agent in agents:
                if (agent.node_id, norm_id) in adoptions:
                    continue  # Already adopted

                # Count fraction of neighbours who adopted this norm
                neighbors = graph.get_neighbors(agent.node_id, "both")
                if not neighbors:
                    continue
                n_adopters = sum(1 for nb in neighbors if nb in adopters)
                frac = n_adopters / len(neighbors)

                if frac >= threshold:
                    new_adoptions.append((agent.node_id, norm_id))

            # Stability bonus for widely-adopted norms
            adoption_frac = len(adopters) / max(1, len(agents))
            if adoption_frac > 0.3:
                norm.state.stability = min(10.0, norm.state.stability + bonus)

        # Apply new adoptions
        for agent_id, norm_id in new_adoptions:
            edge_id = f"norm_{agent_id}_{norm_id}"
            if edge_id not in graph.edges:
                graph.add_edge(GraphEdge(
                    edge_id=edge_id,
                    source_id=agent_id, target_id=norm_id,
                    edge_type=EdgeType.INFORMATION, weight=0.8,
                ))

        # Violation penalty: agents with CONFLICT edges to norms lose energy
        for agent in agents:
            for nb_id in graph.get_neighbors(agent.node_id, "out"):
                edges = graph.get_edges_between(agent.node_id, nb_id)
                for e in edges:
                    if e.edge_type == EdgeType.CONFLICT:
                        target = graph.get_node(nb_id)
                        if target is not None and target.state.custom.get("is_norm", 0.0) >= 1.0:
                            agent.state.energy = max(0.0, agent.state.energy - penalty)
