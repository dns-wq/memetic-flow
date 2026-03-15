"""
Evolutionary competition — replicator dynamics for competing strategies/memes.

Ideas (or strategies) have fitness proportional to their adoption count.
Higher-fitness ideas replicate (gain energy), lower-fitness ideas shrink.
Mutation introduces variation by probabilistically perturbing state.

Based on replicator dynamics from evolutionary game theory
(Taylor & Jonker 1978, Nowak 2006).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec


class EvolutionaryTemplate(DynamicsTemplate):
    name = "evolutionary"
    description = "Replicator dynamics for competing ideas/strategies"
    required_node_types = [NodeType.IDEA]
    required_edge_types = []
    parameters = {
        "selection_strength": ParameterSpec(0.1, 0.0, 1.0, "How strongly fitness differences affect reproduction"),
        "mutation_rate": ParameterSpec(0.01, 0.0, 0.2, "Probability of state perturbation per step"),
        "carrying_capacity": ParameterSpec(100.0, 1.0, 10000.0, "Total energy cap across all ideas"),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        selection = p["selection_strength"]
        mutation = p["mutation_rate"]
        capacity = p["carrying_capacity"]

        ideas = graph.nodes_by_type(NodeType.IDEA)
        if not ideas:
            return

        # Compute fitness for each idea (proxy: adoption = number of incoming edges)
        fitnesses: dict[str, float] = {}
        for idea in ideas:
            incoming = len(graph.get_neighbors(idea.node_id, "in"))
            fitnesses[idea.node_id] = 1.0 + selection * incoming

        total_fitness = sum(fitnesses.values())
        if total_fitness == 0:
            return

        total_energy = sum(n.state.energy for n in ideas)

        # Replicator update: energy grows proportional to relative fitness
        for idea in ideas:
            rel_fitness = fitnesses[idea.node_id] / total_fitness
            avg_fitness = total_fitness / len(ideas)
            rel_advantage = fitnesses[idea.node_id] / avg_fitness

            # Logistic growth toward carrying capacity share
            target = capacity * rel_fitness
            growth = selection * (target - idea.state.energy)
            idea.state.energy = max(0.001, idea.state.energy + growth)

            # Mutation: random perturbation
            if rng.random() < mutation:
                idea.state.mutation_rate = max(
                    0.001,
                    idea.state.mutation_rate + rng.normal(0, 0.005),
                )
                idea.state.energy *= (1.0 + rng.normal(0, 0.05))
                idea.state.energy = max(0.001, idea.state.energy)

        # Normalize to carrying capacity
        total = sum(n.state.energy for n in ideas)
        if total > capacity:
            scale = capacity / total
            for idea in ideas:
                idea.state.energy *= scale
