"""
Population ecology — birth/death, carrying capacity, and species
interactions (predation, competition, mutualism).

Extends classic Lotka-Volterra dynamics to typed network topology.
Species interact through CONFLICT (predation/competition) and
COOPERATION (mutualism) edges.

Priors from quantitative ecology (May 1974, Lotka-Volterra).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class PopulationEcologyTemplate(DynamicsTemplate):
    name = "population_ecology"
    description = "Lotka-Volterra population dynamics with predation and mutualism"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "birth_rate": ParameterSpec(
            0.1, 0.0, 1.0,
            "Base birth rate per species per step",
        ),
        "death_rate": ParameterSpec(
            0.05, 0.0, 1.0,
            "Base death rate per species per step",
        ),
        "carrying_capacity": ParameterSpec(
            100.0, 1.0, 10000.0,
            "Maximum population per species",
        ),
        "predation_rate": ParameterSpec(
            0.02, 0.0, 0.5,
            "Rate at which predators consume prey via CONFLICT edges",
        ),
        "mutualism_coefficient": ParameterSpec(
            0.01, 0.0, 0.2,
            "Benefit from mutualistic partners via COOPERATION edges",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        birth = p["birth_rate"]
        death = p["death_rate"]
        K = p["carrying_capacity"]
        predation = p["predation_rate"]
        mutualism = p["mutualism_coefficient"]

        # Species can be AGENT or RESOURCE nodes
        species = [
            n for n in list(graph.nodes.values())
            if n.node_type in (NodeType.AGENT, NodeType.RESOURCE)
        ]
        if not species:
            return

        # --- Bootstrap population ---
        for sp in species:
            if "population" not in sp.state.custom:
                sp.state.custom["population"] = sp.state.resources * 10.0

        # --- Read current state ---
        deltas: dict[str, float] = {}

        for sp in species:
            pop = sp.state.custom.get("population", 10.0)
            if pop <= 0:
                deltas[sp.node_id] = 0.0
                continue

            # Logistic growth
            growth = birth * pop * (1.0 - pop / K) - death * pop

            # Predation (CONFLICT edges) and mutualism (COOPERATION edges)
            # NOTE: get_edges_between is directional (source→target only),
            # so we must check both directions explicitly.
            for nb_id in graph.get_neighbors(sp.node_id, "both"):
                nb = graph.get_node(nb_id)
                if nb is None:
                    continue
                nb_pop = nb.state.custom.get("population", 10.0)

                # Outgoing edges (sp → nb): sp is predator/initiator
                for e in graph.get_edges_between(sp.node_id, nb_id):
                    if e.edge_type == EdgeType.CONFLICT:
                        # sp preys on nb → sp gains
                        growth += predation * pop * nb_pop / K
                    elif e.edge_type == EdgeType.COOPERATION:
                        growth += mutualism * nb_pop

                # Incoming edges (nb → sp): sp is prey/recipient
                for e in graph.get_edges_between(nb_id, sp.node_id):
                    if e.edge_type == EdgeType.CONFLICT:
                        # nb preys on sp → sp loses
                        growth -= predation * nb_pop * pop / K
                    elif e.edge_type == EdgeType.COOPERATION:
                        growth += mutualism * nb_pop

            deltas[sp.node_id] = growth

        # --- Apply ---
        for sp in species:
            pop = sp.state.custom.get("population", 10.0)
            new_pop = max(0.0, pop + deltas.get(sp.node_id, 0.0))
            new_pop = min(K * 2.0, new_pop)  # Hard cap at 2x carrying capacity
            sp.state.custom["population"] = new_pop

            # Reflect population in energy for visualization
            sp.state.energy = max(0.1, new_pop / K * 5.0)
            sp.state.resources = new_pop / 10.0
