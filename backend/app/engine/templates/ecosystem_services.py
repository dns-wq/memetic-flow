"""
Ecosystem services — mapping ecological states to human-relevant
services with tipping points.

Computes aggregate service value from species diversity × habitat
quality.  Services collapse non-linearly when biodiversity drops below
critical thresholds.

Priors from ecosystem service valuation (Costanza et al., MEA, IPBES).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec


class EcosystemServicesTemplate(DynamicsTemplate):
    name = "ecosystem_services"
    description = "Ecosystem service valuation with biodiversity tipping points"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "biodiversity_threshold": ParameterSpec(
            0.3, 0.0, 1.0,
            "Fraction of species below which services collapse non-linearly",
        ),
        "service_sensitivity": ParameterSpec(
            1.0, 0.1, 5.0,
            "Scaling factor for service output",
        ),
        "collapse_steepness": ParameterSpec(
            5.0, 1.0, 20.0,
            "Steepness of the tipping-point collapse curve",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        bio_thresh = p["biodiversity_threshold"]
        sensitivity = p["service_sensitivity"]
        steepness = p["collapse_steepness"]

        habitats = list(graph.nodes_by_type(NodeType.ENVIRONMENT))
        species = [
            n for n in list(graph.nodes.values())
            if n.node_type in (NodeType.AGENT, NodeType.RESOURCE)
            and n.state.custom.get("population", -1.0) >= 0.0
        ]

        if not habitats:
            return

        # Total species count for biodiversity calculation
        total_species = len(species)
        max_species = max(total_species, 1)

        # Count living species (population > 0)
        living = sum(
            1 for sp in species
            if sp.state.custom.get("population", 0.0) > 0.1
        )
        biodiversity_ratio = living / max_species if max_species > 0 else 0.0

        # --- Tipping point function ---
        # Sigmoid collapse: service = 1 / (1 + exp(-steepness * (ratio - threshold)))
        service_multiplier = 1.0 / (
            1.0 + math.exp(-steepness * (biodiversity_ratio - bio_thresh))
        )

        # --- Compute per-habitat service value ---
        for habitat in habitats:
            quality = habitat.state.custom.get("habitat_quality", 0.5)

            # Count species in this habitat's neighbourhood
            local_species = 0
            for nb_id in graph.get_neighbors(habitat.node_id, "in"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type in (NodeType.AGENT, NodeType.RESOURCE):
                    if nb.state.custom.get("population", 0.0) > 0.1:
                        local_species += 1

            local_diversity = local_species / max(1, total_species)

            # Service value = quality² × local_diversity × global_multiplier × sensitivity
            service_value = (
                quality ** 2
                * local_diversity
                * service_multiplier
                * sensitivity
            )

            habitat.state.custom["service_value"] = service_value
            habitat.state.custom["biodiversity_ratio"] = biodiversity_ratio
            habitat.state.custom["service_multiplier"] = service_multiplier

            # Stability reflects service provision
            habitat.state.stability = max(0.1, service_value * 2.0)

        # --- Global ecosystem health metric ---
        total_service = sum(
            h.state.custom.get("service_value", 0.0) for h in habitats
        )
        for habitat in habitats:
            habitat.state.custom["total_ecosystem_service"] = total_service
