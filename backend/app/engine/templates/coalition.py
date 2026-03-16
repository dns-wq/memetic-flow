"""
Coalition formation — agents forming alliances around shared interests.

Coalitions form when ideologically proximate agents band together.
Coalitions have bargaining power proportional to size.  Members
benefit more inside than outside, but defection temptation exists.

Priors from cooperative game theory (Shapley value, core stability).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, NodeType
from .base import DynamicsTemplate, ParameterSpec


class CoalitionTemplate(DynamicsTemplate):
    name = "coalition"
    description = "Coalition formation with bargaining power and defection dynamics"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "coalition_benefit_multiplier": ParameterSpec(
            1.5, 1.0, 5.0,
            "Resource multiplier for coalition members",
        ),
        "defection_temptation": ParameterSpec(
            0.3, 0.0, 1.0,
            "Attractiveness of leaving a coalition for better options",
        ),
        "minimum_viable_size": ParameterSpec(
            3.0, 2.0, 20.0,
            "Minimum members for a viable coalition",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        benefit = p["coalition_benefit_multiplier"]
        temptation = p["defection_temptation"]
        min_size = int(p["minimum_viable_size"])

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not agents:
            return

        # --- Bootstrap coalition IDs ---
        for agent in agents:
            if "coalition_id" not in agent.state.custom:
                agent.state.custom["coalition_id"] = -1.0  # Unaffiliated

        # --- Phase 1: Coalition benefit distribution ---
        coalitions: dict[int, list] = {}
        for agent in agents:
            cid = int(agent.state.custom.get("coalition_id", -1))
            if cid >= 0:
                coalitions.setdefault(cid, []).append(agent)

        for cid, members in coalitions.items():
            if len(members) < min_size:
                # Dissolve small coalitions
                for m in members:
                    m.state.custom["coalition_id"] = -1.0
                continue
            # Bargaining power ∝ size
            power = math.log(1 + len(members))
            per_member = 0.05 * benefit * power / len(members)
            for m in members:
                m.state.resources += per_member

        # --- Phase 2: Defection ---
        for cid, members in list(coalitions.items()):
            if len(members) < min_size:
                continue
            # Compute internal cohesion (average ideological distance)
            positions = [
                m.state.ideological_position for m in members
                if m.state.ideological_position
            ]
            if len(positions) < 2:
                continue
            ndim = min(len(p) for p in positions)
            mean_pos = [
                sum(p[d] for p in positions) / len(positions)
                for d in range(ndim)
            ]

            for member in members:
                if not member.state.ideological_position:
                    continue
                # Distance from coalition mean
                dist = math.sqrt(sum(
                    (member.state.ideological_position[d] - mean_pos[d]) ** 2
                    for d in range(ndim)
                ))
                # Higher distance + temptation → more likely to defect
                defect_prob = temptation * dist
                if rng.random() < defect_prob:
                    member.state.custom["coalition_id"] = -1.0

        # --- Phase 3: Formation — unaffiliated agents seek coalitions ---
        unaffiliated = [
            a for a in agents
            if int(a.state.custom.get("coalition_id", -1)) < 0
        ]

        if len(unaffiliated) < min_size:
            return

        # Simple: pair unaffiliated agents with nearest unaffiliated neighbours
        for agent in unaffiliated:
            if int(agent.state.custom.get("coalition_id", -1)) >= 0:
                continue
            if not agent.state.ideological_position:
                continue

            # Find nearby unaffiliated agents
            cluster = [agent]
            ndim = len(agent.state.ideological_position)

            for other in unaffiliated:
                if other.node_id == agent.node_id:
                    continue
                if int(other.state.custom.get("coalition_id", -1)) >= 0:
                    continue
                if not other.state.ideological_position:
                    continue
                dist = math.sqrt(sum(
                    (agent.state.ideological_position[d] - other.state.ideological_position[d]) ** 2
                    for d in range(min(ndim, len(other.state.ideological_position)))
                ))
                if dist < 0.3:
                    cluster.append(other)

            if len(cluster) >= min_size:
                new_cid = graph.timestep * 100 + rng.integers(100)
                for m in cluster:
                    m.state.custom["coalition_id"] = float(new_cid)
