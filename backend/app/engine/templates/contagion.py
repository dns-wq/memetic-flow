"""
Contagion dynamics — SIR/SIS/SEIR epidemic-style spreading on networks.

Models viral content, adoption cascades, panic propagation, or actual
disease-like spreading.  Each node has a compartmental state stored in
``custom["contagion_state"]``:  0 = susceptible, 1 = exposed,
2 = infected, 3 = recovered.

Priors from epidemiology (Kermack–McKendrick 1927, Pastor-Satorras
& Vespignani 2001 for networks).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from .base import DynamicsTemplate, ParameterSpec

# Compartmental state codes
_S, _E, _I, _R = 0, 1, 2, 3


class ContagionTemplate(DynamicsTemplate):
    name = "contagion"
    description = "SIR/SIS/SEIR epidemic-style spreading on networks"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "infection_rate": ParameterSpec(
            0.05, 0.001, 1.0,
            "Probability of transmission per infected neighbour per step",
        ),
        "recovery_rate": ParameterSpec(
            0.02, 0.001, 1.0,
            "Probability of recovering per step",
        ),
        "immunity_duration": ParameterSpec(
            0.0, 0.0, 1000.0,
            "Steps of immunity after recovery (0 = permanent / SIR)",
        ),
        "latent_period": ParameterSpec(
            0.0, 0.0, 50.0,
            "Steps in exposed state before becoming infectious (0 = SIR/SIS, >0 = SEIR)",
        ),
        "initial_infected_frac": ParameterSpec(
            0.05, 0.0, 1.0,
            "Fraction of nodes infected at initialisation (first call only)",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        beta = p["infection_rate"]
        gamma = p["recovery_rate"]
        immunity = p["immunity_duration"]
        latent = p["latent_period"]
        init_frac = p["initial_infected_frac"]

        nodes = list(graph.nodes.values())
        if not nodes:
            return

        # Bootstrap compartmental state on first call
        needs_init = not any(
            "contagion_state" in n.state.custom for n in nodes
        )
        if needs_init:
            for n in nodes:
                n.state.custom["contagion_state"] = float(_S)
                n.state.custom["contagion_timer"] = 0.0
            # Seed initial infections
            n_infect = max(1, int(len(nodes) * init_frac))
            seeds = rng.choice(len(nodes), size=min(n_infect, len(nodes)), replace=False)
            for idx in seeds:
                nodes[idx].state.custom["contagion_state"] = float(_I)

        # Collect transitions (read-then-write)
        transitions: dict[str, tuple[float, float]] = {}  # node_id → (new_state, new_timer)

        for node in nodes:
            state = int(node.state.custom.get("contagion_state", _S))
            timer = node.state.custom.get("contagion_timer", 0.0)

            if state == _S:
                # Count infected neighbours
                infected_neighbours = 0
                for nb_id in graph.get_neighbors(node.node_id, "both"):
                    nb = graph.get_node(nb_id)
                    if int(nb.state.custom.get("contagion_state", _S)) == _I:
                        infected_neighbours += 1
                # Probability of remaining susceptible
                if infected_neighbours > 0:
                    p_escape = (1.0 - beta) ** infected_neighbours
                    if rng.random() > p_escape:
                        if latent > 0:
                            transitions[node.node_id] = (float(_E), 0.0)
                        else:
                            transitions[node.node_id] = (float(_I), 0.0)

            elif state == _E:
                # Latent period
                if timer >= latent:
                    transitions[node.node_id] = (float(_I), 0.0)
                else:
                    transitions[node.node_id] = (float(_E), timer + 1.0)

            elif state == _I:
                # Recovery
                if rng.random() < gamma:
                    if immunity > 0 or immunity == 0:
                        # immunity == 0 means permanent (SIR)
                        transitions[node.node_id] = (float(_R), 0.0)
                    else:
                        transitions[node.node_id] = (float(_S), 0.0)

            elif state == _R:
                # Waning immunity (SIS-like if immunity_duration > 0)
                if immunity > 0 and timer >= immunity:
                    transitions[node.node_id] = (float(_S), 0.0)
                elif immunity > 0:
                    transitions[node.node_id] = (float(_R), timer + 1.0)
                # else: permanent immunity, stay in R

        # Apply transitions
        for node_id, (new_state, new_timer) in transitions.items():
            node = graph.get_node(node_id)
            node.state.custom["contagion_state"] = new_state
            node.state.custom["contagion_timer"] = new_timer
            # Reflect infection in energy for visualization
            if int(new_state) == _I:
                node.state.energy = max(node.state.energy, 2.0)
            elif int(new_state) == _R:
                node.state.energy *= 0.8
