"""
Game-theoretic dynamics — agents play repeated games with strategy updates.

Supports configurable 2×2 games (prisoner's dilemma, coordination,
hawk-dove).  Agents update strategies via imitation dynamics: they
copy the strategy of a better-performing neighbour with probability
proportional to the payoff difference.

Based on evolutionary game theory on networks (Szabó & Fáth 2007).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from .base import DynamicsTemplate, ParameterSpec

# Default payoff matrix: Prisoner's Dilemma
# Strategy 0 = Cooperate, Strategy 1 = Defect
# Payoffs are (row_player, col_player)
_DEFAULT_CC = 3.0  # mutual cooperation
_DEFAULT_CD = 0.0  # sucker payoff
_DEFAULT_DC = 5.0  # temptation
_DEFAULT_DD = 1.0  # mutual defection


class GameTheoryTemplate(DynamicsTemplate):
    name = "game_theory"
    description = "Repeated 2×2 games with imitation-based strategy updates"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "payoff_cc": ParameterSpec(
            _DEFAULT_CC, -10.0, 10.0, "Payoff for mutual cooperation",
        ),
        "payoff_cd": ParameterSpec(
            _DEFAULT_CD, -10.0, 10.0, "Payoff for cooperator vs defector",
        ),
        "payoff_dc": ParameterSpec(
            _DEFAULT_DC, -10.0, 10.0, "Payoff for defector vs cooperator",
        ),
        "payoff_dd": ParameterSpec(
            _DEFAULT_DD, -10.0, 10.0, "Payoff for mutual defection",
        ),
        "noise": ParameterSpec(
            0.1, 0.0, 5.0,
            "Selection noise (higher = more random imitation)",
        ),
        "initial_cooperator_frac": ParameterSpec(
            0.5, 0.0, 1.0,
            "Fraction of initial cooperators",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        payoff_matrix = [
            [p["payoff_cc"], p["payoff_cd"]],
            [p["payoff_dc"], p["payoff_dd"]],
        ]
        noise = p["noise"]
        init_coop = p["initial_cooperator_frac"]

        nodes = list(graph.nodes.values())
        if not nodes:
            return

        # Bootstrap strategy on first call
        needs_init = not any(
            "game_strategy" in n.state.custom for n in nodes
        )
        if needs_init:
            for n in nodes:
                n.state.custom["game_strategy"] = (
                    0.0 if rng.random() < init_coop else 1.0
                )
                n.state.custom["game_payoff"] = 0.0

        # Phase 1: Play games with all neighbours, accumulate payoff
        payoffs: dict[str, float] = {n.node_id: 0.0 for n in nodes}

        for node in nodes:
            my_strat = int(node.state.custom.get("game_strategy", 0))
            for nb_id in graph.get_neighbors(node.node_id, "both"):
                nb = graph.get_node(nb_id)
                nb_strat = int(nb.state.custom.get("game_strategy", 0))
                payoffs[node.node_id] += payoff_matrix[my_strat][nb_strat]

        # Store payoffs
        for node in nodes:
            node.state.custom["game_payoff"] = payoffs[node.node_id]

        # Phase 2: Strategy update via Fermi imitation
        new_strategies: dict[str, float] = {}

        for node in nodes:
            neighbours = graph.get_neighbors(node.node_id, "both")
            if not neighbours:
                new_strategies[node.node_id] = node.state.custom.get("game_strategy", 0.0)
                continue

            # Pick a random neighbour
            nb_id = neighbours[rng.integers(len(neighbours))]
            nb = graph.get_node(nb_id)

            my_payoff = payoffs[node.node_id]
            nb_payoff = payoffs[nb_id]

            # Fermi function: probability of adopting neighbour's strategy
            if noise > 0:
                diff = (nb_payoff - my_payoff) / max(noise, 1e-8)
                prob = 1.0 / (1.0 + np.exp(-diff))
            else:
                prob = 1.0 if nb_payoff > my_payoff else 0.0

            if rng.random() < prob:
                new_strategies[node.node_id] = nb.state.custom.get("game_strategy", 0.0)
            else:
                new_strategies[node.node_id] = node.state.custom.get("game_strategy", 0.0)

        # Apply strategy updates and reflect in node state
        for node in nodes:
            node.state.custom["game_strategy"] = new_strategies[node.node_id]
            # Cooperators get higher influence for visualization
            if int(new_strategies[node.node_id]) == 0:
                node.state.influence = min(1.0, node.state.influence + 0.01)
            else:
                node.state.influence = max(0.1, node.state.influence - 0.01)
            # Energy reflects accumulated payoff
            node.state.energy = max(0.1, 1.0 + payoffs[node.node_id] * 0.1)
