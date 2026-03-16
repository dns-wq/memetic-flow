"""
Institutional emergence — cooperation-driven institution formation.

Tracks pairwise cooperation between agents.  When a cluster of agents
exceeds a cohesion threshold, an Institution node is created and
members are linked via MEMBERSHIP edges.  Institutions impose
behavioural constraints on members and can collapse when cohesion
decays below a critical level.

Priors from institutional economics (Douglass North, Acemoglu & Robinson).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, GraphNode, NodeState, NodeType
from .base import DynamicsTemplate, ParameterSpec

_MIN_CLUSTER = 3


class InstitutionalTemplate(DynamicsTemplate):
    name = "institutional"
    description = "Cooperation-driven institution formation and decay"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "formation_threshold": ParameterSpec(
            0.6, 0.1, 1.0,
            "Average cooperation score needed to form an institution",
        ),
        "cohesion_decay": ParameterSpec(
            0.005, 0.0, 0.1,
            "Rate at which institutional membership edge weights decay per step",
        ),
        "constraint_strength": ParameterSpec(
            0.3, 0.0, 1.0,
            "How strongly institutions reduce member mutation rates",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        threshold = p["formation_threshold"]
        decay = p["cohesion_decay"]
        constraint = p["constraint_strength"]

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not agents:
            return

        # --- Phase 1: Update cooperation scores between connected agents ---
        for agent in agents:
            for nb_id in graph.get_neighbors(agent.node_id, "both"):
                nb = graph.get_node(nb_id)
                if nb is None or nb.node_type != NodeType.AGENT:
                    continue
                edges = graph.get_edges_between(agent.node_id, nb_id)
                coop_edges = [e for e in edges if e.edge_type == EdgeType.COOPERATION]
                # Cooperation score rises with cooperation edges, decays otherwise
                key = f"coop_{nb_id}"
                old = agent.state.custom.get(key, 0.0)
                if coop_edges:
                    new_val = min(1.0, old + 0.05)
                else:
                    new_val = max(0.0, old - 0.01)
                agent.state.custom[key] = new_val

        # --- Phase 2: Institutional constraint on members ---
        institutions = list(graph.nodes_by_type(NodeType.INSTITUTION))
        for inst in institutions:
            members = graph.get_institution_members(inst.node_id)
            for mid in members:
                member = graph.get_node(mid)
                if member is not None:
                    member.state.mutation_rate *= (1.0 - constraint)

        # --- Phase 3: Decay institutional cohesion ---
        for inst in institutions:
            members = graph.get_institution_members(inst.node_id)
            if not members:
                continue
            # Decay membership edge weights
            total_weight = 0.0
            n_edges = 0
            for mid in members:
                edges = graph.get_edges_between(mid, inst.node_id)
                for e in edges:
                    if e.edge_type == EdgeType.MEMBERSHIP:
                        e.weight = max(0.0, e.weight - decay)
                        total_weight += e.weight
                        n_edges += 1
            # Collapse if average weight too low
            avg_weight = total_weight / max(1, n_edges)
            if avg_weight < 0.2 and n_edges > 0:
                # Collapse institution
                for mid in list(members):
                    graph.assign_institution(mid, None)
                inst.state.energy = 0.0
                inst.state.stability = 0.0

        # --- Phase 4: Formation — find new clusters ---
        unaffiliated = [a for a in agents if a.institution_id is None]
        unaffiliated_ids = {a.node_id for a in unaffiliated}

        visited: set[str] = set()
        for agent in unaffiliated:
            if agent.node_id in visited:
                continue
            # Greedily find cooperating neighbours
            cluster = {agent.node_id}
            for nb_id in graph.get_neighbors(agent.node_id, "both"):
                if nb_id not in unaffiliated_ids or nb_id in visited:
                    continue
                key = f"coop_{nb_id}"
                score = agent.state.custom.get(key, 0.0)
                if score >= threshold:
                    cluster.add(nb_id)

            if len(cluster) >= _MIN_CLUSTER:
                inst_id = f"inst_tmpl_{graph.timestep}_{agent.node_id[:6]}"
                inst_node = GraphNode(
                    node_id=inst_id,
                    node_type=NodeType.INSTITUTION,
                    label=f"Institution-{graph.timestep}",
                    state=NodeState(
                        resources=2.0, stability=2.0,
                        influence=1.5, energy=2.0,
                    ),
                    institution_id=inst_id,
                )
                graph.add_node(inst_node)
                for cid in cluster:
                    graph.assign_institution(cid, inst_id)
                    graph.add_edge(GraphEdge(
                        edge_id=f"mem_{cid}_{inst_id}",
                        source_id=cid, target_id=inst_id,
                        edge_type=EdgeType.MEMBERSHIP, weight=1.0,
                    ))
                    visited.add(cid)
                    unaffiliated_ids.discard(cid)
