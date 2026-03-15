"""
Memory landscape — shared cultural memory as a global field.

Agents read from and write to a shared memory pool.  Popular memories
gain inertia; forgotten ideas fade.  Old ideas can resurface when
conditions change (historical resonance).

The global memory is stored in ``custom["memory_*"]`` fields on a
dedicated Environment node named ``__memory_pool__``.  Each node
maintains ``custom["memory_contribution"]`` and
``custom["memory_retrieval"]`` tracking its interaction with the pool.
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import GraphNode, NodeState, NodeType
from .base import DynamicsTemplate, ParameterSpec

_POOL_ID = "__memory_pool__"
_MEM_PREFIX = "mem_"


class MemoryLandscapeTemplate(DynamicsTemplate):
    name = "memory_landscape"
    description = "Shared cultural memory with persistence, decay, and resonance"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "memory_persistence": ParameterSpec(
            0.95, 0.0, 1.0,
            "Fraction of memory retained per step (1 = perfect, 0 = instant forget)",
        ),
        "retrieval_threshold": ParameterSpec(
            0.1, 0.0, 1.0,
            "Minimum memory strength for retrieval to affect agents",
        ),
        "resonance_amplification": ParameterSpec(
            1.5, 1.0, 5.0,
            "Multiplier when a new event resonates with existing memory",
        ),
        "write_rate": ParameterSpec(
            0.1, 0.0, 1.0,
            "How strongly each agent writes to shared memory per step",
        ),
        "read_rate": ParameterSpec(
            0.05, 0.0, 1.0,
            "How strongly shared memory influences agent state",
        ),
        "num_memory_slots": ParameterSpec(
            8.0, 1.0, 64.0,
            "Number of distinct memory slots in the landscape",
        ),
    }

    def _ensure_pool(self, graph: DynamicsGraph, n_slots: int) -> GraphNode:
        """Create the memory pool node if it doesn't exist."""
        if not graph.has_node(_POOL_ID):
            pool = GraphNode(
                node_id=_POOL_ID,
                node_type=NodeType.ENVIRONMENT,
                label="Cultural Memory Pool",
                state=NodeState(energy=0.0, stability=1.0),
            )
            graph.add_node(pool)
            for i in range(n_slots):
                pool.state.custom[f"{_MEM_PREFIX}{i}"] = 0.0
        return graph.get_node(_POOL_ID)

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        persistence = p["memory_persistence"]
        threshold = p["retrieval_threshold"]
        resonance = p["resonance_amplification"]
        write_rate = p["write_rate"]
        read_rate = p["read_rate"]
        n_slots = int(p["num_memory_slots"])

        pool = self._ensure_pool(graph, n_slots)

        # Gather non-pool nodes
        active_nodes = [
            n for n in graph.nodes.values() if n.node_id != _POOL_ID
        ]
        if not active_nodes:
            return

        # Phase 1: Decay — memories fade
        for i in range(n_slots):
            key = f"{_MEM_PREFIX}{i}"
            old_val = pool.state.custom.get(key, 0.0)
            pool.state.custom[key] = old_val * persistence

        # Phase 2: Write — agents contribute to collective memory
        for node in active_nodes:
            # Each agent writes to a slot based on a hash of their state
            slot = hash(node.node_id) % n_slots
            key = f"{_MEM_PREFIX}{slot}"
            contribution = node.state.energy * write_rate

            current = pool.state.custom.get(key, 0.0)

            # Resonance: if memory already exists, amplify
            if current > threshold:
                contribution *= resonance

            pool.state.custom[key] = current + contribution
            node.state.custom["memory_contribution"] = contribution

        # Phase 3: Read — collective memory influences agents
        # Compute total memory strength for visualization
        total_memory = sum(
            pool.state.custom.get(f"{_MEM_PREFIX}{i}", 0.0)
            for i in range(n_slots)
        )
        pool.state.energy = total_memory

        for node in active_nodes:
            # Each agent reads from slots closest to its hash neighbourhood
            slot = hash(node.node_id) % n_slots
            # Read from primary slot and adjacent slots
            slots_to_read = [
                slot,
                (slot + 1) % n_slots,
                (slot - 1) % n_slots,
            ]
            retrieved = 0.0
            for s in slots_to_read:
                key = f"{_MEM_PREFIX}{s}"
                val = pool.state.custom.get(key, 0.0)
                if val > threshold:
                    retrieved += val

            node.state.custom["memory_retrieval"] = retrieved

            # Memory influences node energy (cultural resonance effect)
            if retrieved > 0:
                node.state.energy += retrieved * read_rate
                # Cap energy to prevent explosion
                node.state.energy = min(node.state.energy, 50.0)
