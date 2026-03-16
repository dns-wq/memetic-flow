"""
Memetic energy conservation — zero-sum idea competition.

Total memetic energy is approximately conserved.  Energy flows from
low-fitness to high-fitness ideas via network edges.  Small injection
and dissipation rates keep the system near equilibrium.  Creates
narrative feedback cycles where ideas periodically resurface.

Priors from thermodynamic analogies in cultural evolution.
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class MemeticEnergyTemplate(DynamicsTemplate):
    name = "memetic_energy"
    description = "Conserved energy pool distributed among ideas via competitive transfer"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "total_energy": ParameterSpec(
            100.0, 1.0, 10000.0,
            "Target total memetic energy in the system",
        ),
        "injection_rate": ParameterSpec(
            0.1, 0.0, 5.0,
            "New energy injected per step",
        ),
        "dissipation_rate": ParameterSpec(
            0.05, 0.0, 5.0,
            "Energy dissipated (lost) per step",
        ),
        "transfer_efficiency": ParameterSpec(
            0.8, 0.1, 1.0,
            "Fraction of energy preserved during transfer between ideas",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        target_energy = p["total_energy"]
        injection = p["injection_rate"]
        dissipation = p["dissipation_rate"]
        efficiency = p["transfer_efficiency"]

        ideas = list(graph.nodes_by_type(NodeType.IDEA))
        if not ideas:
            return

        # --- Phase 1: Energy transfer from low-fitness to high-fitness ---
        # Fitness = in-degree weighted energy (ideas that receive more attention)
        fitness: dict[str, float] = {}
        for idea in ideas:
            in_neighbors = graph.get_neighbors(idea.node_id, "in")
            in_weight = sum(
                e.weight
                for nid in in_neighbors
                for e in graph.get_edges_between(nid, idea.node_id)
            )
            fitness[idea.node_id] = idea.state.energy * (1.0 + in_weight * 0.1)

        avg_fitness = sum(fitness.values()) / max(1, len(fitness))

        transfers: dict[str, float] = {idea.node_id: 0.0 for idea in ideas}

        for idea in ideas:
            f = fitness[idea.node_id]
            if f < avg_fitness:
                # Lose energy proportional to deficit
                loss = 0.05 * (avg_fitness - f) / max(1.0, avg_fitness)
                loss = min(loss, idea.state.energy * 0.2)  # Cap at 20% per step
                transfers[idea.node_id] -= loss
            else:
                # Gain energy from edges
                gain = 0.05 * (f - avg_fitness) / max(1.0, avg_fitness) * efficiency
                transfers[idea.node_id] += gain

        # Apply transfers
        for idea in ideas:
            idea.state.energy = max(
                0.01, idea.state.energy + transfers[idea.node_id]
            )

        # --- Phase 2: Injection and dissipation ---
        current_total = sum(i.state.energy for i in ideas)

        # Inject energy proportionally to low-energy ideas
        if injection > 0 and ideas:
            per_idea = injection / len(ideas)
            for idea in ideas:
                if idea.state.energy < current_total / max(1, len(ideas)):
                    idea.state.energy += per_idea

        # Dissipate from high-energy ideas
        if dissipation > 0 and ideas:
            per_idea = dissipation / len(ideas)
            for idea in ideas:
                if idea.state.energy > current_total / max(1, len(ideas)):
                    idea.state.energy = max(0.01, idea.state.energy - per_idea)

        # --- Phase 3: Soft normalization toward target ---
        new_total = sum(i.state.energy for i in ideas)
        if new_total > 0 and abs(new_total - target_energy) > target_energy * 0.1:
            scale = target_energy / new_total
            # Gentle correction (10% per step toward target)
            correction = 1.0 + 0.1 * (scale - 1.0)
            for idea in ideas:
                idea.state.energy = max(0.01, idea.state.energy * correction)
