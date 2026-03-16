"""
Knowledge production — researchers discover on a knowledge landscape.

Agent nodes explore a knowledge space.  Discovery probability depends
on agent skill, the frontier state, and collaboration with neighbours.
Knowledge builds cumulatively with prerequisites.

Priors from science of science (de Solla Price, Uzzi et al.).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, GraphNode, NodeState, NodeType
from .base import DynamicsTemplate, ParameterSpec


class KnowledgeProductionTemplate(DynamicsTemplate):
    name = "knowledge_production"
    description = "Researchers discover knowledge with prerequisites and collaboration"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "discovery_probability": ParameterSpec(
            0.01, 0.0, 0.2,
            "Base probability of discovery per researcher per step",
        ),
        "prerequisite_depth": ParameterSpec(
            2.0, 0.0, 10.0,
            "Required number of connected knowledge ideas before discovery",
        ),
        "collaboration_bonus": ParameterSpec(
            0.1, 0.0, 1.0,
            "Discovery probability bonus per connected researcher",
        ),
        "serendipity_rate": ParameterSpec(
            0.001, 0.0, 0.05,
            "Probability of breakthrough without prerequisites",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        base_prob = p["discovery_probability"]
        prereq_depth = int(p["prerequisite_depth"])
        collab_bonus = p["collaboration_bonus"]
        serendipity = p["serendipity_rate"]

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not agents:
            return

        # --- Bootstrap researcher skill ---
        for agent in agents:
            if "researcher_skill" not in agent.state.custom:
                agent.state.custom["researcher_skill"] = float(
                    rng.uniform(0.3, 1.0)
                )
            if "discoveries" not in agent.state.custom:
                agent.state.custom["discoveries"] = 0.0

        # --- Phase 1: Discovery attempts ---
        new_discoveries: list[tuple[str, GraphNode]] = []

        for agent in agents:
            skill = agent.state.custom.get("researcher_skill", 0.5)

            # Count connected knowledge (ideas)
            connected_ideas = 0
            for nb_id in graph.get_neighbors(agent.node_id, "out"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type == NodeType.IDEA:
                    connected_ideas += 1

            # Count collaborating researchers
            collaborators = 0
            for nb_id in graph.get_neighbors(agent.node_id, "both"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type == NodeType.AGENT:
                    collaborators += 1

            # Prerequisites met?
            has_prerequisites = connected_ideas >= prereq_depth

            # Compute discovery probability
            if has_prerequisites:
                prob = base_prob * skill * (1.0 + collab_bonus * collaborators)
            else:
                prob = serendipity * skill

            prob = min(1.0, prob)

            if rng.random() < prob:
                disc_id = f"disc_{graph.timestep}_{agent.node_id[:8]}_{rng.integers(100000)}"
                discovery = GraphNode(
                    node_id=disc_id,
                    node_type=NodeType.IDEA,
                    label=f"Discovery-{graph.timestep}",
                    state=NodeState(
                        energy=2.0, stability=1.5,
                        influence=0.5,
                    ),
                    metadata={"discoverer": agent.node_id},
                )
                discovery.state.custom["evidence_strength"] = float(
                    rng.uniform(0.5, 1.0)
                )
                discovery.state.custom["citation_count"] = 0.0
                new_discoveries.append((agent.node_id, discovery))

        # Apply discoveries (limit to prevent explosion)
        for creator_id, disc_node in new_discoveries[:3]:
            graph.add_node(disc_node)
            # Link to creator
            graph.add_edge(GraphEdge(
                edge_id=f"authored_{creator_id}_{disc_node.node_id}",
                source_id=creator_id, target_id=disc_node.node_id,
                edge_type=EdgeType.INFORMATION, weight=1.0,
            ))
            # Update creator stats
            creator = graph.get_node(creator_id)
            if creator is not None:
                creator.state.custom["discoveries"] = (
                    creator.state.custom.get("discoveries", 0.0) + 1.0
                )
                creator.state.influence += 0.1

        # --- Phase 2: Citation / knowledge building ---
        ideas = list(graph.nodes_by_type(NodeType.IDEA))
        for idea in ideas:
            if idea.state.custom.get("citation_count") is None:
                continue
            # Ideas with high evidence attract citations (incoming edges)
            evidence = idea.state.custom.get("evidence_strength", 0.5)
            idea.state.energy = max(
                0.1, 1.0 + idea.state.custom.get("citation_count", 0.0) * 0.1
            )

        # --- Phase 3: Skill growth from collaboration ---
        for agent in agents:
            collab_count = 0
            for nb_id in graph.get_neighbors(agent.node_id, "both"):
                nb = graph.get_node(nb_id)
                if nb is not None and nb.node_type == NodeType.AGENT:
                    collab_count += 1
            if collab_count > 0:
                agent.state.custom["researcher_skill"] = min(
                    2.0,
                    agent.state.custom.get("researcher_skill", 0.5)
                    + 0.001 * collab_count,
                )
