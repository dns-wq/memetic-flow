"""
Paradigm dynamics — normal science and paradigm shifts.

Knowledge organises into paradigms (Institution nodes).  Normal science
accumulates knowledge within a paradigm.  Anomalies build when
observations conflict.  When anomalies exceed a crisis threshold, a
competing paradigm can take over.

Priors from Thomas Kuhn's *Structure of Scientific Revolutions*.
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, GraphEdge, NodeType
from .base import DynamicsTemplate, ParameterSpec


class ParadigmTemplate(DynamicsTemplate):
    name = "paradigm"
    description = "Normal science with anomaly accumulation and paradigm shifts"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "anomaly_accumulation_rate": ParameterSpec(
            0.05, 0.0, 0.5,
            "Rate at which conflicting ideas generate anomalies",
        ),
        "crisis_threshold": ParameterSpec(
            5.0, 1.0, 50.0,
            "Anomaly count that triggers a paradigm crisis",
        ),
        "paradigm_inertia": ParameterSpec(
            0.8, 0.0, 1.0,
            "Resistance to paradigm change (higher = more inertia)",
        ),
        "switching_cost": ParameterSpec(
            0.5, 0.0, 5.0,
            "Energy penalty for agents switching paradigms",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        anomaly_rate = p["anomaly_accumulation_rate"]
        crisis_thresh = p["crisis_threshold"]
        inertia = p["paradigm_inertia"]
        switch_cost = p["switching_cost"]

        paradigms = list(graph.nodes_by_type(NodeType.INSTITUTION))
        ideas = list(graph.nodes_by_type(NodeType.IDEA))
        agents = list(graph.nodes_by_type(NodeType.AGENT))

        if not paradigms:
            return

        # --- Bootstrap ---
        for par in paradigms:
            if "anomaly_count" not in par.state.custom:
                par.state.custom["anomaly_count"] = 0.0
            if "is_paradigm" not in par.state.custom:
                par.state.custom["is_paradigm"] = 1.0

        # --- Phase 1: Normal science — paradigm members gain bonus ---
        for par in paradigms:
            if par.state.custom.get("is_paradigm", 0.0) < 1.0:
                continue
            members = graph.get_institution_members(par.node_id)
            for mid in members:
                member = graph.get_node(mid)
                if member is not None:
                    member.state.energy = min(
                        10.0, member.state.energy + 0.02
                    )

        # --- Phase 2: Anomaly accumulation ---
        for par in paradigms:
            if par.state.custom.get("is_paradigm", 0.0) < 1.0:
                continue
            members = graph.get_institution_members(par.node_id)
            # Ideas held by members that conflict with the paradigm
            for mid in members:
                for nb_id in graph.get_neighbors(mid, "out"):
                    nb = graph.get_node(nb_id)
                    if nb is None or nb.node_type != NodeType.IDEA:
                        continue
                    # Check for conflict edges between idea and paradigm
                    edges = graph.get_edges_between(nb_id, par.node_id)
                    has_conflict = any(
                        e.edge_type == EdgeType.CONFLICT for e in edges
                    )
                    if has_conflict:
                        par.state.custom["anomaly_count"] = (
                            par.state.custom.get("anomaly_count", 0.0)
                            + anomaly_rate
                        )

            # Natural decay of anomalies (paradigm self-correction)
            par.state.custom["anomaly_count"] = max(
                0.0,
                par.state.custom.get("anomaly_count", 0.0) - 0.01,
            )

        # --- Phase 3: Crisis and paradigm shift ---
        in_crisis = [
            par for par in paradigms
            if par.state.custom.get("anomaly_count", 0.0) >= crisis_thresh
            and par.state.custom.get("is_paradigm", 0.0) >= 1.0
        ]

        if not in_crisis:
            return

        # Find competing paradigms (other institutions)
        for crisis_par in in_crisis:
            competitors = [
                par for par in paradigms
                if par.node_id != crisis_par.node_id
                and par.state.custom.get("is_paradigm", 0.0) >= 1.0
            ]
            if not competitors:
                continue

            # Best competitor by energy
            best = max(competitors, key=lambda x: x.state.energy)

            # Shift probability: inversely proportional to inertia
            shift_prob = (1.0 - inertia) * (
                crisis_par.state.custom.get("anomaly_count", 0.0) / crisis_thresh
            )

            if rng.random() < shift_prob:
                # Paradigm shift! Members of crisis paradigm switch to competitor
                members = list(graph.get_institution_members(crisis_par.node_id))
                for mid in members:
                    member = graph.get_node(mid)
                    if member is None:
                        continue
                    graph.assign_institution(mid, best.node_id)
                    member.state.energy = max(
                        0.1, member.state.energy - switch_cost
                    )
                    # Add membership edge to new paradigm
                    edge_id = f"shift_{mid}_{best.node_id}_{graph.timestep}"
                    try:
                        graph.add_edge(GraphEdge(
                            edge_id=edge_id,
                            source_id=mid, target_id=best.node_id,
                            edge_type=EdgeType.MEMBERSHIP, weight=0.8,
                        ))
                    except (KeyError, ValueError):
                        pass

                # Crisis paradigm loses status
                crisis_par.state.custom["anomaly_count"] = 0.0
                crisis_par.state.energy *= 0.3
                crisis_par.state.stability *= 0.5

                # Competitor gains
                best.state.energy += 2.0
                best.state.stability += 1.0
