"""
Memetic field dynamics — ideas as attractors in conceptual space.

Ideas exist in N-dimensional ideological-position space and exert
attractive forces (inverse-square) on agents.  Agents drift through
the conceptual field, forming ideological gravity wells.

Priors from memetics (Dawkins), cultural attraction theory (Sperber).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec


class MemeticFieldTemplate(DynamicsTemplate):
    name = "memetic_field"
    description = "Ideas exert attractive forces on agents in conceptual space"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "field_strength": ParameterSpec(
            0.1, 0.0, 1.0,
            "Base attractive force of ideas on agents",
        ),
        "conceptual_friction": ParameterSpec(
            0.3, 0.0, 1.0,
            "Damping factor that slows agent drift through conceptual space",
        ),
        "escape_velocity": ParameterSpec(
            2.0, 0.1, 10.0,
            "Force threshold above which agents can break free of a gravity well",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        strength = p["field_strength"]
        friction = p["conceptual_friction"]

        ideas = [
            n for n in graph.nodes_by_type(NodeType.IDEA)
            if n.state.ideological_position
        ]
        agents = [
            n for n in graph.nodes_by_type(NodeType.AGENT)
            if n.state.ideological_position
        ]

        if not ideas or not agents:
            return

        ndim = min(
            len(agents[0].state.ideological_position),
            len(ideas[0].state.ideological_position),
        )

        # --- Compute forces on each agent ---
        forces: dict[str, list[float]] = {}

        for agent in agents:
            a_pos = agent.state.ideological_position[:ndim]
            net_force = [0.0] * ndim

            for idea in ideas:
                i_pos = idea.state.ideological_position[:ndim]
                # Distance in conceptual space
                diff = [i_pos[d] - a_pos[d] for d in range(ndim)]
                dist_sq = sum(d * d for d in diff) + 0.01  # Avoid division by zero
                dist = math.sqrt(dist_sq)

                # Inverse-square attractive force weighted by idea energy
                magnitude = strength * idea.state.energy / dist_sq
                for d in range(ndim):
                    net_force[d] += magnitude * (diff[d] / dist)

            forces[agent.node_id] = net_force

        # --- Apply drift with friction ---
        for agent in agents:
            force = forces.get(agent.node_id)
            if force is None:
                continue
            pos = agent.state.ideological_position[:ndim]
            new_pos = [
                max(0.0, min(1.0, pos[d] + force[d] * (1.0 - friction)))
                for d in range(ndim)
            ]
            agent.state.ideological_position = new_pos

            # Store force magnitude for visualization
            force_mag = math.sqrt(sum(f * f for f in force))
            agent.state.custom["field_force"] = force_mag

        # --- Detect gravity wells ---
        # A gravity well exists when an idea captures agents within a small radius
        for idea in ideas:
            i_pos = idea.state.ideological_position[:ndim]
            captured = 0
            for agent in agents:
                a_pos = agent.state.ideological_position[:ndim]
                dist = math.sqrt(sum(
                    (i_pos[d] - a_pos[d]) ** 2 for d in range(ndim)
                ))
                if dist < 0.15:
                    captured += 1
            idea.state.custom["gravity_well_size"] = float(captured)
