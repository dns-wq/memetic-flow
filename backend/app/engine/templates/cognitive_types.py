"""
Cognitive heterogeneity — four cognitive archetypes with different
information-processing strategies.

Archetypes: heuristic (0), probabilistic (1), ideological (2),
strategic (3).  Each responds differently to information from
neighbours.  Archetype distribution shifts based on relative success.

Priors from bounded rationality (Herbert Simon), dual-process theory
(Kahneman & Tversky).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec

# Archetype codes
_HEURISTIC, _PROBABILISTIC, _IDEOLOGICAL, _STRATEGIC = 0, 1, 2, 3


class CognitiveTypesTemplate(DynamicsTemplate):
    name = "cognitive_types"
    description = "Four cognitive archetypes with different info-processing strategies"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "strategy_switch_probability": ParameterSpec(
            0.05, 0.0, 0.5,
            "Probability per step that a low-performing agent switches archetype",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        switch_prob = p["strategy_switch_probability"]

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not agents:
            return

        # --- Bootstrap ---
        needs_init = not any(
            "cognitive_type" in a.state.custom for a in agents
        )
        if needs_init:
            for a in agents:
                a.state.custom["cognitive_type"] = float(rng.integers(0, 4))
                a.state.custom["cog_prev_resources"] = a.state.resources

        # --- Phase 1: Apply archetype-specific behaviour ---
        position_deltas: dict[str, list[float]] = {}

        for agent in agents:
            ctype = int(agent.state.custom.get("cognitive_type", 0))
            neighbors = graph.get_neighbors(agent.node_id, "both")
            if not neighbors or not agent.state.ideological_position:
                continue

            nb_nodes = [
                graph.get_node(nid) for nid in neighbors
            ]
            nb_nodes = [
                n for n in nb_nodes
                if n is not None and n.state.ideological_position
            ]
            if not nb_nodes:
                continue

            pos = list(agent.state.ideological_position)
            ndim = len(pos)

            if ctype == _HEURISTIC:
                # Follow the trend: copy the highest-energy neighbour's position
                best = max(nb_nodes, key=lambda n: n.state.energy)
                delta = [
                    0.1 * (best.state.ideological_position[d] - pos[d])
                    for d in range(min(ndim, len(best.state.ideological_position)))
                ]
                position_deltas[agent.node_id] = delta

            elif ctype == _PROBABILISTIC:
                # Bayesian: weighted mean of neighbours by energy
                total_e = sum(n.state.energy for n in nb_nodes) + 1e-10
                mean_pos = [0.0] * ndim
                for n in nb_nodes:
                    w = n.state.energy / total_e
                    for d in range(min(ndim, len(n.state.ideological_position))):
                        mean_pos[d] += w * n.state.ideological_position[d]
                delta = [0.05 * (mean_pos[d] - pos[d]) for d in range(ndim)]
                position_deltas[agent.node_id] = delta

            elif ctype == _IDEOLOGICAL:
                # Resist change: very small movement toward mean
                total_e = sum(n.state.energy for n in nb_nodes) + 1e-10
                mean_pos = [0.0] * ndim
                for n in nb_nodes:
                    w = n.state.energy / total_e
                    for d in range(min(ndim, len(n.state.ideological_position))):
                        mean_pos[d] += w * n.state.ideological_position[d]
                delta = [0.01 * (mean_pos[d] - pos[d]) for d in range(ndim)]
                position_deltas[agent.node_id] = delta

            elif ctype == _STRATEGIC:
                # Maximize own gain: move toward position that maximises resource neighbours
                richest = sorted(nb_nodes, key=lambda n: n.state.resources, reverse=True)
                if richest:
                    target = richest[0]
                    delta = [
                        0.08 * (target.state.ideological_position[d] - pos[d])
                        for d in range(min(ndim, len(target.state.ideological_position)))
                    ]
                    position_deltas[agent.node_id] = delta

        # Apply position updates
        for agent in agents:
            delta = position_deltas.get(agent.node_id)
            if delta and agent.state.ideological_position:
                new_pos = [
                    max(0.0, min(1.0, agent.state.ideological_position[d] + delta[d]))
                    for d in range(len(agent.state.ideological_position))
                ]
                agent.state.ideological_position = new_pos

        # --- Phase 2: Strategy switching ---
        # Agents with declining resources may switch to a better-performing archetype
        type_performance: dict[int, list[float]] = {i: [] for i in range(4)}
        for agent in agents:
            ctype = int(agent.state.custom.get("cognitive_type", 0))
            prev = agent.state.custom.get("cog_prev_resources", agent.state.resources)
            perf = agent.state.resources - prev
            type_performance[ctype].append(perf)
            agent.state.custom["cog_prev_resources"] = agent.state.resources

        avg_perf = {
            t: (sum(v) / len(v) if v else 0.0)
            for t, v in type_performance.items()
        }
        best_type = max(avg_perf, key=lambda t: avg_perf[t])

        for agent in agents:
            ctype = int(agent.state.custom.get("cognitive_type", 0))
            prev = agent.state.custom.get("cog_prev_resources", agent.state.resources)
            if agent.state.resources < prev and rng.random() < switch_prob:
                agent.state.custom["cognitive_type"] = float(best_type)
