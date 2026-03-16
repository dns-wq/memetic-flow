"""
Habitat dynamics — quality, degradation, restoration, fragmentation.

ENVIRONMENT nodes represent habitats with quality and area attributes.
Quality degrades from occupant pressure and recovers through
restoration.  Fragmentation isolates populations when connectivity
drops below threshold.

Priors from landscape ecology (Hanski, MacArthur & Wilson).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class HabitatTemplate(DynamicsTemplate):
    name = "habitat"
    description = "Habitat quality dynamics with degradation, restoration, and fragmentation"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "degradation_rate": ParameterSpec(
            0.01, 0.0, 0.2,
            "Rate at which occupant pressure degrades habitat quality",
        ),
        "restoration_rate": ParameterSpec(
            0.005, 0.0, 0.1,
            "Rate of natural habitat quality restoration",
        ),
        "connectivity_threshold": ParameterSpec(
            0.3, 0.0, 1.0,
            "Minimum habitat connectivity to prevent population isolation",
        ),
        "migration_sensitivity": ParameterSpec(
            0.1, 0.0, 1.0,
            "How strongly species migrate toward higher-quality habitats",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        degrade = p["degradation_rate"]
        restore = p["restoration_rate"]
        conn_thresh = p["connectivity_threshold"]
        migration_sens = p["migration_sensitivity"]

        habitats = list(graph.nodes_by_type(NodeType.ENVIRONMENT))
        if not habitats:
            return

        # --- Bootstrap ---
        for h in habitats:
            if "habitat_quality" not in h.state.custom:
                h.state.custom["habitat_quality"] = 0.8
            if "habitat_area" not in h.state.custom:
                h.state.custom["habitat_area"] = 1.0

        # --- Phase 1: Degradation from occupant pressure ---
        for h in habitats:
            quality = h.state.custom.get("habitat_quality", 0.8)
            # Count occupants (agents/resources connected to this habitat)
            occupants = 0
            total_pop = 0.0
            for nb_id in graph.get_neighbors(h.node_id, "in"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type in (NodeType.AGENT, NodeType.RESOURCE):
                    occupants += 1
                    total_pop += nb.state.custom.get("population", 1.0)

            pressure = degrade * total_pop / max(1.0, h.state.custom.get("habitat_area", 1.0) * 100.0)
            new_quality = max(0.0, quality - pressure)

            # Restoration
            new_quality += restore * (1.0 - new_quality)  # Diminishing returns

            h.state.custom["habitat_quality"] = min(1.0, new_quality)
            h.state.energy = new_quality * 3.0  # Visualization

        # --- Phase 2: Connectivity / fragmentation ---
        for h in habitats:
            # Count connections to other habitats
            habitat_connections = 0
            for nb_id in graph.get_neighbors(h.node_id, "both"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type == NodeType.ENVIRONMENT:
                    habitat_connections += 1

            connectivity = min(1.0, habitat_connections / max(1, len(habitats) - 1))
            h.state.custom["connectivity"] = connectivity

            # Fragmentation penalty: if connectivity below threshold, populations decline
            if connectivity < conn_thresh:
                fragmentation_penalty = 0.02 * (conn_thresh - connectivity)
                for nb_id in graph.get_neighbors(h.node_id, "in"):
                    nb = graph.get_node(nb_id)
                    if nb is not None and nb.node_type in (NodeType.AGENT, NodeType.RESOURCE):
                        pop = nb.state.custom.get("population", 1.0)
                        nb.state.custom["population"] = max(
                            0.0, pop * (1.0 - fragmentation_penalty)
                        )

        # --- Phase 3: Migration toward better habitats ---
        if len(habitats) < 2:
            return

        species = [
            n for n in list(graph.nodes.values())
            if n.node_type in (NodeType.AGENT, NodeType.RESOURCE)
        ]

        for sp in species:
            # Find which habitats this species is connected to
            connected_habitats = []
            for nb_id in graph.get_neighbors(sp.node_id, "out"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type == NodeType.ENVIRONMENT:
                    connected_habitats.append(nb)

            if len(connected_habitats) < 2:
                continue

            # Migration: shift resources toward higher-quality habitat
            best = max(connected_habitats, key=lambda h: h.state.custom.get("habitat_quality", 0.5))
            worst = min(connected_habitats, key=lambda h: h.state.custom.get("habitat_quality", 0.5))

            quality_diff = (
                best.state.custom.get("habitat_quality", 0.5)
                - worst.state.custom.get("habitat_quality", 0.5)
            )
            if quality_diff > 0.1:
                migration_flow = migration_sens * quality_diff * sp.state.resources * 0.1
                sp.state.resources += migration_flow * 0.5  # Net benefit of moving
