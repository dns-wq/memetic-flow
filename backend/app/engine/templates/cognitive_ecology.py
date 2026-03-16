"""
Cognitive ecology — agent phenotypes with reproduction and extinction.

Agents have cognitive phenotypes (persuasion, learning, deception,
cooperation) that determine interaction outcomes.  Successful agents
reproduce; failing agents go extinct.

Priors from evolutionary ecology (Robert May, John Maynard Smith).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, GraphNode, NodeState, NodeType
from .base import DynamicsTemplate, ParameterSpec

_PHENO_KEYS = ["pheno_persuasion", "pheno_learning", "pheno_deception", "pheno_cooperation"]


class CognitiveEcologyTemplate(DynamicsTemplate):
    name = "cognitive_ecology"
    description = "Agent phenotype evolution with reproduction and extinction"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "reproduction_threshold": ParameterSpec(
            5.0, 1.0, 20.0,
            "Resource level above which an agent reproduces",
        ),
        "extinction_threshold": ParameterSpec(
            0.1, 0.0, 1.0,
            "Resource level below which an agent goes extinct",
        ),
        "phenotype_mutation_std": ParameterSpec(
            0.05, 0.0, 0.5,
            "Standard deviation of phenotype mutation during reproduction",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        repro_thresh = p["reproduction_threshold"]
        extinct_thresh = p["extinction_threshold"]
        mut_std = p["phenotype_mutation_std"]

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not agents:
            return

        # --- Bootstrap phenotypes on first call ---
        needs_init = not any(
            _PHENO_KEYS[0] in a.state.custom for a in agents
        )
        if needs_init:
            for a in agents:
                for key in _PHENO_KEYS:
                    a.state.custom[key] = float(rng.uniform(0.2, 0.8))

        # --- Phase 1: Pairwise interactions ---
        # Each agent interacts with a random neighbour
        for agent in agents:
            neighbors = graph.get_neighbors(agent.node_id, "both")
            if not neighbors:
                continue
            nb_id = rng.choice(neighbors)
            nb = graph.get_node(nb_id)
            if nb is None or nb.node_type != NodeType.AGENT:
                continue

            # Interaction outcome: persuasion vs deception
            a_attack = agent.state.custom.get("pheno_persuasion", 0.5)
            b_defend = nb.state.custom.get("pheno_deception", 0.5)
            # Cooperation bonus when both have high cooperation
            a_coop = agent.state.custom.get("pheno_cooperation", 0.5)
            b_coop = nb.state.custom.get("pheno_cooperation", 0.5)
            mutual_coop = a_coop * b_coop

            if mutual_coop > 0.3:
                # Cooperative: both gain
                gain = 0.1 * mutual_coop
                agent.state.resources += gain
                nb.state.resources += gain
            else:
                # Competitive: persuader extracts from defender
                delta = 0.1 * max(0.0, a_attack - b_defend)
                agent.state.resources += delta
                nb.state.resources = max(0.0, nb.state.resources - delta)

            # Learning: improve weakest phenotype slightly
            learn_rate = agent.state.custom.get("pheno_learning", 0.5) * 0.01
            weakest = min(_PHENO_KEYS, key=lambda k: agent.state.custom.get(k, 0.5))
            agent.state.custom[weakest] = min(
                1.0, agent.state.custom.get(weakest, 0.5) + learn_rate
            )

        # --- Phase 2: Reproduction ---
        new_agents: list[tuple[GraphNode, str]] = []
        for agent in agents:
            if agent.state.resources >= repro_thresh:
                child_id = f"child_{graph.timestep}_{agent.node_id[:8]}"
                child = GraphNode(
                    node_id=child_id,
                    node_type=NodeType.AGENT,
                    label=f"Offspring-{graph.timestep}",
                    state=NodeState(
                        resources=agent.state.resources * 0.4,
                        energy=1.0, stability=1.0, influence=0.3,
                    ),
                )
                # Inherit phenotype with mutation
                for key in _PHENO_KEYS:
                    parent_val = agent.state.custom.get(key, 0.5)
                    child.state.custom[key] = float(np.clip(
                        parent_val + rng.normal(0, mut_std), 0.0, 1.0
                    ))
                new_agents.append((child, agent.node_id))
                agent.state.resources *= 0.5  # Cost of reproduction

        for child, parent_id in new_agents:
            graph.add_node(child)
            graph.add_edge(GraphEdge(
                edge_id=f"spawn_{parent_id}_{child.node_id}",
                source_id=parent_id, target_id=child.node_id,
                edge_type=EdgeType.COOPERATION, weight=0.5,
            ))

        # --- Phase 3: Extinction ---
        to_remove: list[str] = []
        for agent in agents:
            if agent.state.resources < extinct_thresh:
                to_remove.append(agent.node_id)

        for nid in to_remove:
            graph.remove_node(nid)
