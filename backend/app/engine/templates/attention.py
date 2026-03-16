"""
Attention economy — finite shared attention competing among ideas.

Attention is a global pool distributed among IDEA nodes based on their
energy, novelty, and recency.  Ideas with high attention boost the
influence of connected agents.  Follows power-law dynamics.

Priors from attention economics (Herbert Simon, Tim Wu).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec


class AttentionTemplate(DynamicsTemplate):
    name = "attention"
    description = "Finite attention pool distributed among ideas via power-law competition"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "total_attention_pool": ParameterSpec(
            100.0, 1.0, 10000.0,
            "Total attention available in the system per step",
        ),
        "novelty_weight": ParameterSpec(
            0.5, 0.0, 2.0,
            "Weight of novelty in attention allocation",
        ),
        "recency_decay": ParameterSpec(
            0.02, 0.0, 0.5,
            "Exponential decay rate for idea age in attention calculation",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        pool = p["total_attention_pool"]
        novelty_w = p["novelty_weight"]
        decay = p["recency_decay"]

        ideas = list(graph.nodes_by_type(NodeType.IDEA))
        if not ideas:
            return

        # --- Bootstrap age tracking ---
        for idea in ideas:
            if "attention_age" not in idea.state.custom:
                idea.state.custom["attention_age"] = 0.0

        # --- Compute raw attention scores ---
        scores: list[float] = []
        for idea in ideas:
            age = idea.state.custom.get("attention_age", 0.0)
            recency = math.exp(-decay * age)
            novelty = idea.state.custom.get("novelty", 0.5) * novelty_w
            raw = max(0.001, idea.state.energy * recency * (1.0 + novelty))
            scores.append(raw)

        # Normalize to pool (softmax-like)
        total = sum(scores)
        if total < 1e-10:
            return

        # --- Distribute attention ---
        updates: dict[str, float] = {}
        for idea, score in zip(ideas, scores):
            share = (score / total) * pool
            updates[idea.node_id] = share

        # Apply
        for idea in ideas:
            share = updates.get(idea.node_id, 0.0)
            idea.state.custom["attention_share"] = share
            idea.state.custom["attention_age"] = (
                idea.state.custom.get("attention_age", 0.0) + 1.0
            )

            # High-attention ideas boost connected agents' influence
            if share > pool / max(1, len(ideas)) * 1.5:  # Above average
                boost = 0.02 * (share / pool)
                for nb_id in graph.get_neighbors(idea.node_id, "in"):
                    nb = graph.get_node(nb_id)
                    if nb is not None and nb.node_type == NodeType.AGENT:
                        nb.state.influence = min(
                            5.0, nb.state.influence + boost
                        )
