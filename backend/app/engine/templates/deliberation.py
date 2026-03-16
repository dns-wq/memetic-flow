"""
Deliberation dynamics — argument exchange with evidence weighting.

Agents exchange arguments (ideas) weighted by evidence strength.
Confirmation bias causes agents to discount arguments far from their
position.  A deliberation quality metric tracks whether the group
converges on well-supported positions.

Priors from deliberative democracy (Habermas, Fishkin).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec


class DeliberationTemplate(DynamicsTemplate):
    name = "deliberation"
    description = "Argument exchange with evidence weight and confirmation bias"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "evidence_weight": ParameterSpec(
            0.5, 0.0, 2.0,
            "How much evidence quality affects opinion shifts",
        ),
        "confirmation_bias": ParameterSpec(
            0.3, 0.0, 1.0,
            "Degree to which agents discount disagreeable arguments",
        ),
        "argument_decay": ParameterSpec(
            0.02, 0.0, 0.2,
            "Rate at which old arguments lose persuasive power",
        ),
        "engagement_selectivity": ParameterSpec(
            0.5, 0.0, 1.0,
            "How selectively agents engage (high = echo chamber tendency)",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        ev_weight = p["evidence_weight"]
        bias = p["confirmation_bias"]
        decay = p["argument_decay"]
        selectivity = p["engagement_selectivity"]

        agents = [
            a for a in graph.nodes_by_type(NodeType.AGENT)
            if a.state.ideological_position
        ]
        ideas = list(graph.nodes_by_type(NodeType.IDEA))

        if not agents:
            return

        # --- Bootstrap argument evidence ---
        for idea in ideas:
            if "evidence_strength" not in idea.state.custom:
                idea.state.custom["evidence_strength"] = float(
                    rng.uniform(0.1, 1.0)
                )
            if "argument_age" not in idea.state.custom:
                idea.state.custom["argument_age"] = 0.0

        # --- Phase 1: Argument aging and decay ---
        for idea in ideas:
            idea.state.custom["argument_age"] = (
                idea.state.custom.get("argument_age", 0.0) + 1.0
            )
            # Persuasiveness decays with age
            age = idea.state.custom["argument_age"]
            idea.state.custom["persuasiveness"] = (
                idea.state.custom.get("evidence_strength", 0.5)
                * math.exp(-decay * age)
            )

        # --- Phase 2: Agent-to-agent deliberation ---
        position_deltas: dict[str, list[float]] = {}

        for agent in agents:
            neighbors = graph.get_neighbors(agent.node_id, "both")
            if not neighbors:
                continue

            ndim = len(agent.state.ideological_position)
            net_shift = [0.0] * ndim
            total_weight = 0.0

            for nb_id in neighbors:
                nb = graph.get_node(nb_id)
                if nb is None or not nb.state.ideological_position:
                    continue
                if nb.node_type != NodeType.AGENT:
                    continue

                nb_ndim = min(ndim, len(nb.state.ideological_position))

                # Ideological distance
                dist = math.sqrt(sum(
                    (agent.state.ideological_position[d] - nb.state.ideological_position[d]) ** 2
                    for d in range(nb_ndim)
                ))

                # Selective engagement: skip distant agents with probability ∝ selectivity
                if rng.random() < selectivity * dist:
                    continue

                # Confirmation bias: discount arguments from distant positions
                discount = 1.0 - bias * min(1.0, dist)
                discount = max(0.1, discount)

                # Evidence weight from connected ideas
                shared_ideas_ev = 0.5  # Base evidence
                for idea_id in graph.get_neighbors(nb_id, "out"):
                    idea = graph.get_node(idea_id)
                    if idea is not None and idea.node_type == NodeType.IDEA:
                        shared_ideas_ev = max(
                            shared_ideas_ev,
                            idea.state.custom.get("persuasiveness", 0.5),
                        )

                w = ev_weight * discount * shared_ideas_ev
                for d in range(nb_ndim):
                    net_shift[d] += w * (
                        nb.state.ideological_position[d] - agent.state.ideological_position[d]
                    )
                total_weight += w

            if total_weight > 0:
                position_deltas[agent.node_id] = [
                    s / total_weight * 0.1 for s in net_shift
                ]

        # --- Apply shifts ---
        for agent in agents:
            delta = position_deltas.get(agent.node_id)
            if delta:
                ndim = len(agent.state.ideological_position)
                agent.state.ideological_position = [
                    max(0.0, min(1.0, agent.state.ideological_position[d] + delta[d]))
                    for d in range(ndim)
                ]

        # --- Phase 3: Compute deliberation quality ---
        # Quality = correlation between evidence strength and position convergence
        if ideas and agents:
            high_ev_ideas = [i for i in ideas if i.state.custom.get("evidence_strength", 0) > 0.7]
            if high_ev_ideas:
                # What fraction of agents are near high-evidence positions?
                near_count = 0
                for agent in agents:
                    for idea in high_ev_ideas:
                        if idea.state.ideological_position:
                            ndim = min(len(agent.state.ideological_position), len(idea.state.ideological_position))
                            dist = math.sqrt(sum(
                                (agent.state.ideological_position[d] - idea.state.ideological_position[d]) ** 2
                                for d in range(ndim)
                            ))
                            if dist < 0.2:
                                near_count += 1
                                break

                quality = near_count / max(1, len(agents))
                for agent in agents:
                    agent.state.custom["deliberation_quality"] = quality
