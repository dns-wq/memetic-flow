"""
Network evolution — the graph topology itself evolves over time.

Agents form and break connections based on homophily (similarity in
ideological position), reciprocity, and triadic closure (friends of
friends).  Edges can also decay if unused.

Based on adaptive network theory (Gross & Blasius 2008, Holme &
Newman 2006).
"""

from __future__ import annotations

import uuid

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge
from .base import DynamicsTemplate, ParameterSpec


def _position_distance(a: list[float], b: list[float]) -> float:
    """Euclidean distance between two ideological position vectors."""
    if not a or not b:
        return 1.0
    dim = min(len(a), len(b))
    return float(np.sqrt(sum((a[i] - b[i]) ** 2 for i in range(dim))))


class NetworkEvolutionTemplate(DynamicsTemplate):
    name = "network_evolution"
    description = "Topology evolution via homophily, reciprocity, and triadic closure"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "rewiring_probability": ParameterSpec(
            0.05, 0.0, 1.0,
            "Probability that each node attempts a rewiring per step",
        ),
        "homophily_strength": ParameterSpec(
            0.8, 0.0, 10.0,
            "How strongly similarity drives new edge formation",
        ),
        "triadic_closure_rate": ParameterSpec(
            0.1, 0.0, 1.0,
            "Probability of connecting to a friend-of-friend",
        ),
        "edge_decay_rate": ParameterSpec(
            0.01, 0.0, 0.5,
            "Probability of dropping a low-weight edge per step",
        ),
        "decay_weight_threshold": ParameterSpec(
            0.2, 0.0, 1.0,
            "Edges below this weight are candidates for decay",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        rewire_prob = p["rewiring_probability"]
        homophily = p["homophily_strength"]
        triadic = p["triadic_closure_rate"]
        decay_rate = p["edge_decay_rate"]
        decay_threshold = p["decay_weight_threshold"]

        nodes = list(graph.nodes.values())
        if len(nodes) < 2:
            return

        node_ids = [n.node_id for n in nodes]

        # Phase 1: Edge decay — remove low-weight edges
        edges_to_remove: list[str] = []
        for edge in list(graph.edges.values()):
            if edge.weight < decay_threshold and rng.random() < decay_rate:
                edges_to_remove.append(edge.edge_id)

        for eid in edges_to_remove:
            if eid in graph.edges:
                graph.remove_edge(eid)

        # Phase 2: Rewiring — each node may form a new edge
        for node in nodes:
            if rng.random() > rewire_prob:
                continue

            current_neighbours = set(graph.get_neighbors(node.node_id, "both"))

            # Triadic closure attempt
            if current_neighbours and rng.random() < triadic:
                # Pick a random neighbour, then pick a random friend-of-friend
                nb_id = list(current_neighbours)[rng.integers(len(current_neighbours))]
                fof = set(graph.get_neighbors(nb_id, "both")) - current_neighbours - {node.node_id}
                if fof:
                    target = list(fof)[rng.integers(len(fof))]
                    self._try_add_edge(graph, node.node_id, target, rng)
                    continue

            # Homophily-based connection
            candidates = [
                nid for nid in node_ids
                if nid != node.node_id and nid not in current_neighbours
            ]
            if not candidates:
                continue

            if homophily > 0 and node.state.ideological_position:
                # Weight candidates by similarity
                distances = []
                for cid in candidates:
                    cn = graph.get_node(cid)
                    d = _position_distance(
                        node.state.ideological_position,
                        cn.state.ideological_position,
                    )
                    distances.append(d)

                # Convert distances to probabilities (closer = higher prob)
                distances_arr = np.array(distances)
                similarity = np.exp(-homophily * distances_arr)
                total = similarity.sum()
                if total > 0:
                    probs = similarity / total
                    idx = rng.choice(len(candidates), p=probs)
                    self._try_add_edge(graph, node.node_id, candidates[idx], rng)
            else:
                # Random attachment
                target = candidates[rng.integers(len(candidates))]
                self._try_add_edge(graph, node.node_id, target, rng)

    def _try_add_edge(
        self,
        graph: DynamicsGraph,
        source: str,
        target: str,
        rng: np.random.Generator,
    ) -> None:
        """Add an edge if one doesn't already exist between source and target."""
        existing = graph.get_edges_between(source, target)
        if existing:
            # Strengthen existing edge instead
            existing[0].weight = min(1.0, existing[0].weight + 0.1)
            return

        edge = GraphEdge(
            edge_id=f"netevo_{uuid.uuid4().hex[:8]}",
            source_id=source,
            target_id=target,
            edge_type=EdgeType.INFLUENCE,
            weight=0.3 + rng.random() * 0.3,
            transfer_rate=0.1,
        )
        graph.add_edge(edge)
