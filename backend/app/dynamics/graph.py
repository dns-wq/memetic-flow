"""
Mutable dynamics graph with history tracking.

DynamicsGraph is the central data structure that all templates
operate on.  It supports CRUD for nodes/edges, neighbour queries,
feedback-loop detection, snapshot capture, and full timeline replay.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from datetime import datetime
from typing import Literal

from .models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    NodeType,
)


class DynamicsGraph:
    """Mutable typed graph with snapshot-based history."""

    def __init__(self, seed: GraphSnapshot | None = None) -> None:
        if seed is not None:
            self._nodes: dict[str, GraphNode] = {
                k: v.model_copy(deep=True) for k, v in seed.nodes.items()
            }
            self._edges: dict[str, GraphEdge] = {
                k: v.model_copy(deep=True) for k, v in seed.edges.items()
            }
            self._institutions: dict[str, list[str]] = copy.deepcopy(
                seed.institutions
            )
            self._timestep: int = seed.timestep
        else:
            self._nodes = {}
            self._edges = {}
            self._institutions: dict[str, list[str]] = {}
            self._timestep = 0

        # Fast adjacency indices (rebuilt lazily)
        self._out_edges: dict[str, list[str]] = defaultdict(list)
        self._in_edges: dict[str, list[str]] = defaultdict(list)
        self._rebuild_adjacency()

        # Timeline of past snapshots
        self._history: list[GraphSnapshot] = []

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        if node.node_id in self._nodes:
            raise ValueError(f"Node {node.node_id!r} already exists")
        self._nodes[node.node_id] = node
        if node.institution_id:
            self._institutions.setdefault(node.institution_id, []).append(
                node.node_id
            )

    def remove_node(self, node_id: str) -> GraphNode:
        node = self._nodes.pop(node_id, None)
        if node is None:
            raise KeyError(f"Node {node_id!r} not found")
        # Remove edges touching this node
        edge_ids = [
            eid
            for eid, e in self._edges.items()
            if e.source_id == node_id or e.target_id == node_id
        ]
        for eid in edge_ids:
            self._remove_edge_internal(eid)
        # Remove from institution
        if node.institution_id and node.institution_id in self._institutions:
            members = self._institutions[node.institution_id]
            if node_id in members:
                members.remove(node_id)
            if not members:
                del self._institutions[node.institution_id]
        return node

    def get_node(self, node_id: str) -> GraphNode:
        try:
            return self._nodes[node_id]
        except KeyError:
            raise KeyError(f"Node {node_id!r} not found")

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def update_node_state(self, node_id: str, **updates: float) -> None:
        """Update one or more state fields on a node."""
        node = self.get_node(node_id)
        for key, value in updates.items():
            if key == "custom":
                raise ValueError("Use update_node_custom() for custom fields")
            if hasattr(node.state, key):
                setattr(node.state, key, value)
            else:
                raise AttributeError(
                    f"NodeState has no field {key!r}. "
                    "Use update_node_custom() for custom fields."
                )

    def update_node_custom(self, node_id: str, **updates: float) -> None:
        """Update custom state fields on a node."""
        node = self.get_node(node_id)
        node.state.custom.update(updates)

    @property
    def nodes(self) -> dict[str, GraphNode]:
        return self._nodes

    def nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.edge_id in self._edges:
            raise ValueError(f"Edge {edge.edge_id!r} already exists")
        if edge.source_id not in self._nodes:
            raise KeyError(f"Source node {edge.source_id!r} not found")
        if edge.target_id not in self._nodes:
            raise KeyError(f"Target node {edge.target_id!r} not found")
        self._edges[edge.edge_id] = edge
        self._out_edges[edge.source_id].append(edge.edge_id)
        self._in_edges[edge.target_id].append(edge.edge_id)

    def remove_edge(self, edge_id: str) -> GraphEdge:
        if edge_id not in self._edges:
            raise KeyError(f"Edge {edge_id!r} not found")
        return self._remove_edge_internal(edge_id)

    def get_edge(self, edge_id: str) -> GraphEdge:
        try:
            return self._edges[edge_id]
        except KeyError:
            raise KeyError(f"Edge {edge_id!r} not found")

    @property
    def edges(self) -> dict[str, GraphEdge]:
        return self._edges

    def edges_by_type(self, edge_type: EdgeType) -> list[GraphEdge]:
        return [e for e in self._edges.values() if e.edge_type == edge_type]

    # ------------------------------------------------------------------
    # Neighbour / topology queries
    # ------------------------------------------------------------------

    def get_neighbors(
        self,
        node_id: str,
        direction: Literal["out", "in", "both"] = "out",
        edge_type: EdgeType | None = None,
    ) -> list[str]:
        """Return neighbour node IDs reachable from *node_id*."""
        result: set[str] = set()
        if direction in ("out", "both"):
            for eid in self._out_edges.get(node_id, []):
                edge = self._edges[eid]
                if edge_type is None or edge.edge_type == edge_type:
                    result.add(edge.target_id)
        if direction in ("in", "both"):
            for eid in self._in_edges.get(node_id, []):
                edge = self._edges[eid]
                if edge_type is None or edge.edge_type == edge_type:
                    result.add(edge.source_id)
        return list(result)

    def get_edges_between(
        self, source_id: str, target_id: str
    ) -> list[GraphEdge]:
        return [
            self._edges[eid]
            for eid in self._out_edges.get(source_id, [])
            if self._edges[eid].target_id == target_id
        ]

    def get_feedback_loops(self, max_length: int = 5) -> list[list[str]]:
        """Find all directed cycles up to *max_length* via DFS."""
        loops: list[list[str]] = []
        visited_global: set[tuple[str, ...]] = set()

        for start in self._nodes:
            stack: list[tuple[str, list[str]]] = [(start, [start])]
            while stack:
                current, path = stack.pop()
                if len(path) > max_length + 1:
                    continue
                for eid in self._out_edges.get(current, []):
                    nxt = self._edges[eid].target_id
                    if nxt == start and len(path) > 1:
                        cycle = tuple(path)
                        canonical = min(
                            tuple(cycle[i:] + cycle[:i])
                            for i in range(len(cycle))
                        )
                        if canonical not in visited_global:
                            visited_global.add(canonical)
                            loops.append(list(cycle))
                    elif nxt not in path and len(path) <= max_length:
                        stack.append((nxt, path + [nxt]))
        return loops

    # ------------------------------------------------------------------
    # Institution helpers
    # ------------------------------------------------------------------

    @property
    def institutions(self) -> dict[str, list[str]]:
        return self._institutions

    def get_institution_members(self, institution_id: str) -> list[str]:
        return self._institutions.get(institution_id, [])

    def assign_institution(self, node_id: str, institution_id: str) -> None:
        node = self.get_node(node_id)
        # Remove from old institution
        if node.institution_id and node.institution_id in self._institutions:
            members = self._institutions[node.institution_id]
            if node_id in members:
                members.remove(node_id)
            if not members:
                del self._institutions[node.institution_id]
        # Assign to new
        node.institution_id = institution_id
        self._institutions.setdefault(institution_id, []).append(node_id)

    # ------------------------------------------------------------------
    # Snapshot / timeline
    # ------------------------------------------------------------------

    @property
    def timestep(self) -> int:
        return self._timestep

    def advance_timestep(self) -> None:
        self._timestep += 1

    def snapshot(self) -> GraphSnapshot:
        """Capture the current graph state as an immutable snapshot."""
        return GraphSnapshot(
            timestep=self._timestep,
            nodes={k: v.model_copy(deep=True) for k, v in self._nodes.items()},
            edges={k: v.model_copy(deep=True) for k, v in self._edges.items()},
            institutions=copy.deepcopy(self._institutions),
            timestamp=datetime.utcnow(),
        )

    def save_snapshot(self, snap: GraphSnapshot | None = None) -> GraphSnapshot:
        """Save a snapshot to the internal history timeline."""
        if snap is None:
            snap = self.snapshot()
        self._history.append(snap)
        return snap

    @property
    def history(self) -> list[GraphSnapshot]:
        return self._history

    def restore(self, snap: GraphSnapshot) -> None:
        """Restore graph state from a snapshot (destructive)."""
        self._nodes = {
            k: v.model_copy(deep=True) for k, v in snap.nodes.items()
        }
        self._edges = {
            k: v.model_copy(deep=True) for k, v in snap.edges.items()
        }
        self._institutions = copy.deepcopy(snap.institutions)
        self._timestep = snap.timestep
        self._rebuild_adjacency()

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Quick stats for debugging / API responses."""
        return {
            "timestep": self._timestep,
            "num_nodes": len(self._nodes),
            "num_edges": len(self._edges),
            "num_institutions": len(self._institutions),
            "node_types": {
                t.value: len(self.nodes_by_type(t)) for t in NodeType
            },
            "edge_types": {
                t.value: len(self.edges_by_type(t)) for t in EdgeType
            },
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _remove_edge_internal(self, edge_id: str) -> GraphEdge:
        edge = self._edges.pop(edge_id)
        out = self._out_edges.get(edge.source_id, [])
        if edge_id in out:
            out.remove(edge_id)
        inp = self._in_edges.get(edge.target_id, [])
        if edge_id in inp:
            inp.remove(edge_id)
        return edge

    def _rebuild_adjacency(self) -> None:
        self._out_edges = defaultdict(list)
        self._in_edges = defaultdict(list)
        for eid, edge in self._edges.items():
            self._out_edges[edge.source_id].append(eid)
            self._in_edges[edge.target_id].append(eid)
