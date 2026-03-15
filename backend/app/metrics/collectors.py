"""
Macro-level metric computation for dynamics graphs.

MetricsCollector computes aggregate measures that turn raw simulation
state into interpretable analysis: entropy, polarization, inequality,
clustering, cascade detection, and energy totals.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np

from ..dynamics.graph import DynamicsGraph
from ..dynamics.models import NodeType, EdgeType


class MetricsCollector:
    """Compute macro-level metrics from a DynamicsGraph snapshot."""

    def compute(self, graph: DynamicsGraph) -> dict[str, float]:
        return {
            "idea_entropy": self._idea_entropy(graph),
            "polarization_index": self._polarization(graph),
            "clustering_coefficient": self._clustering(graph),
            "institutional_cohesion": self._cohesion(graph),
            "resource_gini": self._gini(graph),
            "cascade_count": self._cascades(graph),
            "feedback_loop_strength": self._loop_strength(graph),
            "total_energy": self._total_energy(graph),
            "num_nodes": float(len(graph.nodes)),
            "num_edges": float(len(graph.edges)),
        }

    # ------------------------------------------------------------------
    # Individual metric implementations
    # ------------------------------------------------------------------

    def _idea_entropy(self, graph: DynamicsGraph) -> float:
        """Shannon entropy of idea energy distribution.

        High entropy = ideas are equally energetic (diverse ecosystem).
        Low entropy = one or few ideas dominate.
        """
        ideas = graph.nodes_by_type(NodeType.IDEA)
        if not ideas:
            return 0.0

        energies = [max(n.state.energy, 1e-12) for n in ideas]
        total = sum(energies)
        if total == 0:
            return 0.0

        probs = [e / total for e in energies]
        return -sum(p * math.log2(p) for p in probs if p > 0)

    def _polarization(self, graph: DynamicsGraph) -> float:
        """Polarization index based on ideological positions.

        Measures the bimodality of opinion distributions.
        Returns 0.0 (consensus) to 1.0 (maximally polarized).
        Uses variance of pairwise distances normalized by max possible.
        """
        positions = []
        for node in graph.nodes.values():
            if node.state.ideological_position:
                positions.append(np.array(node.state.ideological_position))

        if len(positions) < 2:
            return 0.0

        # Mean pairwise distance
        dists = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dists.append(float(np.linalg.norm(positions[i] - positions[j])))

        if not dists:
            return 0.0

        mean_dist = np.mean(dists)
        std_dist = np.std(dists)

        # Normalize: high mean distance + low variance = polarized (two camps)
        # Low mean distance = consensus
        if mean_dist == 0:
            return 0.0

        # Polarization increases with mean distance and decreases with
        # variance (two tight clusters vs spread out).
        # Clamp to [0, 1].
        polarization = mean_dist / (1.0 + std_dist)
        return min(1.0, polarization)

    def _clustering(self, graph: DynamicsGraph) -> float:
        """Global clustering coefficient (fraction of closed triplets).

        Treats the graph as undirected for this computation.
        """
        if len(graph.nodes) < 3:
            return 0.0

        # Build undirected adjacency
        adj: dict[str, set[str]] = {nid: set() for nid in graph.nodes}
        for edge in graph.edges.values():
            adj[edge.source_id].add(edge.target_id)
            adj[edge.target_id].add(edge.source_id)

        triangles = 0
        triplets = 0

        for node_id in graph.nodes:
            neighbors = list(adj[node_id])
            k = len(neighbors)
            if k < 2:
                continue
            triplets += k * (k - 1) // 2
            for i in range(len(neighbors)):
                for j in range(i + 1, len(neighbors)):
                    if neighbors[j] in adj[neighbors[i]]:
                        triangles += 1

        if triplets == 0:
            return 0.0
        return triangles / triplets

    def _cohesion(self, graph: DynamicsGraph) -> float:
        """Institutional cohesion: average intra-institutional edge density.

        Higher = members of institutions are tightly connected.
        """
        institutions = graph.institutions
        if not institutions:
            return 0.0

        cohesion_scores: list[float] = []
        for inst_id, members in institutions.items():
            if len(members) < 2:
                continue
            # Count edges between members
            member_set = set(members)
            internal_edges = 0
            for eid, edge in graph.edges.items():
                if edge.source_id in member_set and edge.target_id in member_set:
                    internal_edges += 1
            max_edges = len(members) * (len(members) - 1)  # directed
            density = internal_edges / max_edges if max_edges > 0 else 0.0
            cohesion_scores.append(density)

        return sum(cohesion_scores) / len(cohesion_scores) if cohesion_scores else 0.0

    def _gini(self, graph: DynamicsGraph) -> float:
        """Gini coefficient of resource distribution.

        0 = perfect equality, 1 = maximal inequality.
        """
        resources = sorted(n.state.resources for n in graph.nodes.values())
        n = len(resources)
        if n == 0:
            return 0.0

        total = sum(resources)
        if total == 0:
            return 0.0

        # Standard Gini formula
        cumulative = 0.0
        weighted_sum = 0.0
        for i, r in enumerate(resources):
            cumulative += r
            weighted_sum += (2 * (i + 1) - n - 1) * r

        return weighted_sum / (n * total)

    def _cascades(self, graph: DynamicsGraph) -> float:
        """Count nodes with energy above 2x the mean (active cascades)."""
        energies = [n.state.energy for n in graph.nodes.values()]
        if not energies:
            return 0.0
        mean_e = sum(energies) / len(energies)
        if mean_e == 0:
            return 0.0
        return float(sum(1 for e in energies if e > 2 * mean_e))

    def _loop_strength(self, graph: DynamicsGraph) -> float:
        """Average weight of edges participating in feedback loops."""
        loops = graph.get_feedback_loops(max_length=4)
        if not loops:
            return 0.0

        loop_edge_weights: list[float] = []
        for loop in loops:
            for i in range(len(loop)):
                src = loop[i]
                tgt = loop[(i + 1) % len(loop)]
                edges = graph.get_edges_between(src, tgt)
                for e in edges:
                    loop_edge_weights.append(e.weight)

        return sum(loop_edge_weights) / len(loop_edge_weights) if loop_edge_weights else 0.0

    def _total_energy(self, graph: DynamicsGraph) -> float:
        """Sum of all node energies."""
        return sum(n.state.energy for n in graph.nodes.values())
