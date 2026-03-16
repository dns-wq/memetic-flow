"""
Cultural mutation and inheritance — ideas with transmissibility,
stability, mutation, and recombination.

When agents transmit ideas through INFORMATION edges, copies may
mutate.  Compatible ideas can recombine into new hybrid ideas.
Over time, cultural lineages (families of related ideas) emerge.

Priors from cultural evolution (Cavalli-Sforza & Feldman, Peter
Richerson & Robert Boyd).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, GraphNode, NodeState, NodeType
from .base import DynamicsTemplate, ParameterSpec


class CulturalEvolutionTemplate(DynamicsTemplate):
    name = "cultural_evolution"
    description = "Idea mutation, transmission drift, and recombination into hybrids"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "mutation_rate": ParameterSpec(
            0.02, 0.0, 0.5,
            "Probability that a transmitted idea mutates",
        ),
        "recombination_probability": ParameterSpec(
            0.01, 0.0, 0.2,
            "Probability that two compatible ideas recombine per step",
        ),
        "compatibility_threshold": ParameterSpec(
            0.3, 0.0, 1.0,
            "Maximum ideological distance for ideas to be compatible",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        mut_rate = p["mutation_rate"]
        recomb_prob = p["recombination_probability"]
        compat_thresh = p["compatibility_threshold"]

        ideas = list(graph.nodes_by_type(NodeType.IDEA))
        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not ideas:
            return

        # --- Bootstrap transmissibility and compatibility ---
        for idea in ideas:
            if "transmissibility" not in idea.state.custom:
                idea.state.custom["transmissibility"] = float(rng.uniform(0.3, 0.9))
            if "compatibility" not in idea.state.custom:
                idea.state.custom["compatibility"] = float(rng.uniform(0.2, 0.8))
            if "generation" not in idea.state.custom:
                idea.state.custom["generation"] = 0.0

        # --- Phase 1: Transmission with mutation ---
        new_ideas: list[GraphNode] = []
        new_edges: list[GraphEdge] = []

        for idea in ideas:
            trans = idea.state.custom.get("transmissibility", 0.5)
            # Find INFORMATION edges carrying this idea
            for nb_id in graph.get_neighbors(idea.node_id, "in"):
                nb = graph.get_node(nb_id)
                if nb is None or nb.node_type != NodeType.AGENT:
                    continue
                # Agent transmits to their neighbours with probability ∝ transmissibility
                for target_id in graph.get_neighbors(nb_id, "out"):
                    target = graph.get_node(target_id)
                    if target is None or target.node_type != NodeType.AGENT:
                        continue
                    if rng.random() > trans * 0.1:  # Low per-step rate
                        continue

                    # Mutation?
                    if rng.random() < mut_rate:
                        # Create mutant copy
                        mutant_id = f"mut_{graph.timestep}_{idea.node_id[:6]}_{rng.integers(100000)}"
                        mutant = GraphNode(
                            node_id=mutant_id,
                            node_type=NodeType.IDEA,
                            label=f"Mutant-{idea.label}",
                            state=NodeState(
                                energy=idea.state.energy * 0.8,
                                stability=idea.state.stability * 0.9,
                            ),
                            metadata={"parent": idea.node_id},
                        )
                        # Shift ideological position
                        if idea.state.ideological_position:
                            mutant.state.ideological_position = [
                                max(0.0, min(1.0, v + rng.normal(0, 0.1)))
                                for v in idea.state.ideological_position
                            ]
                        mutant.state.custom["transmissibility"] = float(np.clip(
                            idea.state.custom.get("transmissibility", 0.5)
                            + rng.normal(0, 0.05), 0.1, 1.0
                        ))
                        mutant.state.custom["compatibility"] = float(np.clip(
                            idea.state.custom.get("compatibility", 0.5)
                            + rng.normal(0, 0.05), 0.1, 1.0
                        ))
                        mutant.state.custom["generation"] = (
                            idea.state.custom.get("generation", 0.0) + 1.0
                        )
                        new_ideas.append(mutant)
                        new_edges.append(GraphEdge(
                            edge_id=f"lineage_{idea.node_id}_{mutant_id}",
                            source_id=idea.node_id, target_id=mutant_id,
                            edge_type=EdgeType.INFORMATION, weight=0.5,
                        ))
                    break  # One transmission attempt per agent per step

        # Limit new ideas per step to prevent explosion
        for idea_node in new_ideas[:5]:
            graph.add_node(idea_node)
        for edge in new_edges[:5]:
            try:
                graph.add_edge(edge)
            except (KeyError, ValueError):
                pass

        # --- Phase 2: Recombination ---
        if len(ideas) < 2:
            return

        for _ in range(min(3, len(ideas))):  # Max 3 recombinations per step
            if rng.random() > recomb_prob:
                continue
            # Pick two random ideas
            idx = rng.choice(len(ideas), size=2, replace=False)
            a, b = ideas[idx[0]], ideas[idx[1]]

            # Check compatibility via ideological distance
            if a.state.ideological_position and b.state.ideological_position:
                ndim = min(len(a.state.ideological_position), len(b.state.ideological_position))
                dist = math.sqrt(sum(
                    (a.state.ideological_position[d] - b.state.ideological_position[d]) ** 2
                    for d in range(ndim)
                ))
                if dist > compat_thresh:
                    continue
            else:
                # No position — check compatibility custom field
                ca = a.state.custom.get("compatibility", 0.5)
                cb = b.state.custom.get("compatibility", 0.5)
                if abs(ca - cb) > compat_thresh:
                    continue

            # Create hybrid
            hybrid_id = f"hybrid_{graph.timestep}_{a.node_id[:4]}_{b.node_id[:4]}_{rng.integers(100000)}"
            hybrid = GraphNode(
                node_id=hybrid_id,
                node_type=NodeType.IDEA,
                label=f"Hybrid-{graph.timestep}",
                state=NodeState(
                    energy=(a.state.energy + b.state.energy) * 0.6,
                    stability=max(a.state.stability, b.state.stability),
                ),
                metadata={"parents": [a.node_id, b.node_id]},
            )
            if a.state.ideological_position and b.state.ideological_position:
                ndim = min(len(a.state.ideological_position), len(b.state.ideological_position))
                hybrid.state.ideological_position = [
                    (a.state.ideological_position[d] + b.state.ideological_position[d]) / 2.0
                    for d in range(ndim)
                ]
            hybrid.state.custom["transmissibility"] = (
                a.state.custom.get("transmissibility", 0.5)
                + b.state.custom.get("transmissibility", 0.5)
            ) / 2.0
            hybrid.state.custom["compatibility"] = max(
                a.state.custom.get("compatibility", 0.5),
                b.state.custom.get("compatibility", 0.5),
            )
            hybrid.state.custom["generation"] = max(
                a.state.custom.get("generation", 0.0),
                b.state.custom.get("generation", 0.0),
            ) + 1.0

            graph.add_node(hybrid)
            for parent in [a, b]:
                graph.add_edge(GraphEdge(
                    edge_id=f"recomb_{parent.node_id}_{hybrid_id}",
                    source_id=parent.node_id, target_id=hybrid_id,
                    edge_type=EdgeType.INFORMATION, weight=0.6,
                ))
