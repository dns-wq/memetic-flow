"""
Synthetic Civilizations mode.

Simulates the emergence of institutions, norms, economies, and political
factions from agent interactions.  Agents begin as survival-driven actors;
over time they invent structures through cooperation and competition.
"""

from __future__ import annotations

from typing import Any

from ..dynamics import DynamicsGraph, EdgeType, GraphEdge, GraphNode, NodeState, NodeType
from .base import SimulationMode

# Cohesion threshold: if average edge weight between a cluster of agents
# exceeds this, they may form an institution.
_FORMATION_THRESHOLD = 0.6
_MIN_CLUSTER_SIZE = 3


class SyntheticCivMode(SimulationMode):
    name = "synthetic_civ"
    description = (
        "Simulate institutional emergence, norm formation, and civilizational "
        "dynamics from agent interactions."
    )
    icon = "castle"
    required_templates = ["diffusion", "opinion", "resource", "feedback"]
    optional_templates = ["evolutionary"]
    default_params = {
        "diffusion": {"transfer_rate": 0.04, "decay_rate": 0.005},
        "opinion": {"tolerance": 0.35, "convergence_rate": 0.08},
        "resource": {"growth_rate": 0.03, "competition_coefficient": 0.02},
        "feedback": {"flow_coefficient": 0.12},
    }
    visualization_preset = "force"
    metrics_focus = [
        "institutional_cohesion", "polarization_index",
        "clustering_coefficient", "resource_gini",
    ]
    suggested_for = [
        "policy", "regulation", "governance", "institution",
        "society", "civilization", "political", "government",
    ]

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        # Ensure all agents start with moderate resources and diversity
        for node in base_graph.nodes_by_type(NodeType.AGENT):
            if not node.state.ideological_position:
                # Assign a random-ish 2D ideological position from node_id hash
                h = hash(node.node_id)
                base_graph.update_node_state(
                    node.node_id,
                    ideological_position=[
                        ((h & 0xFF) / 255.0),
                        (((h >> 8) & 0xFF) / 255.0),
                    ],
                )
        return base_graph

    def post_step_hook(
        self, graph: DynamicsGraph, timestep: int
    ) -> list[dict[str, Any]]:
        """Check for emergent institutional formation."""
        events: list[dict[str, Any]] = []

        # Only check every 10 steps to avoid overhead
        if timestep % 10 != 0:
            return events

        # Find agent clusters with high mutual cooperation
        agents = graph.nodes_by_type(NodeType.AGENT)
        unaffiliated = [a for a in agents if a.institution_id is None]

        if len(unaffiliated) < _MIN_CLUSTER_SIZE:
            return events

        # Simple greedy clustering: for each unaffiliated agent, find its
        # strongly-connected neighbors (also unaffiliated)
        unaffiliated_ids = {a.node_id for a in unaffiliated}

        for agent in unaffiliated:
            neighbors = graph.get_neighbors(agent.node_id, direction="both")
            cluster_ids = {agent.node_id}
            for nb_id in neighbors:
                if nb_id not in unaffiliated_ids:
                    continue
                edges = graph.get_edges_between(agent.node_id, nb_id)
                avg_weight = sum(e.weight for e in edges) / max(1, len(edges))
                if avg_weight >= _FORMATION_THRESHOLD:
                    cluster_ids.add(nb_id)

            if len(cluster_ids) >= _MIN_CLUSTER_SIZE:
                # Form a new institution!
                inst_id = f"inst_{timestep}_{agent.node_id[:6]}"
                inst_label = f"Institution-{timestep}"
                inst_node = GraphNode(
                    node_id=inst_id,
                    node_type=NodeType.INSTITUTION,
                    label=inst_label,
                    state=NodeState(resources=2.0, stability=2.0, influence=1.5, energy=2.0),
                    institution_id=inst_id,
                )
                graph.add_node(inst_node)

                for cid in cluster_ids:
                    graph.assign_institution(cid, inst_id)
                    # Add membership edge
                    graph.add_edge(GraphEdge(
                        edge_id=f"mem_{cid}_{inst_id}",
                        source_id=cid,
                        target_id=inst_id,
                        edge_type=EdgeType.MEMBERSHIP,
                        weight=1.0,
                    ))
                    unaffiliated_ids.discard(cid)

                events.append({
                    "timestep": timestep,
                    "event_type": "institution_formed",
                    "description": f"{inst_label} formed with {len(cluster_ids)} members",
                    "data": {"institution_id": inst_id, "member_count": len(cluster_ids)},
                })

        return events
