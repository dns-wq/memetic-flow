"""
Dynamics graph initializer.

Converts ontology definitions and Zep knowledge graph entities into
a DynamicsGraph with properly typed nodes, edges, initial state
values, and suggested dynamical templates.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..dynamics import (
    DynamicsGraph,
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeState,
    NodeType,
)

# ---------------------------------------------------------------------------
# Mapping tables: ontology/Zep labels → dynamics types
# ---------------------------------------------------------------------------

# Entity labels that map to each NodeType.  Checked case-insensitively.
_LABEL_TO_NODE_TYPE: dict[str, NodeType] = {
    # AGENT
    "person": NodeType.AGENT,
    "student": NodeType.AGENT,
    "professor": NodeType.AGENT,
    "journalist": NodeType.AGENT,
    "celebrity": NodeType.AGENT,
    "executive": NodeType.AGENT,
    "official": NodeType.AGENT,
    "lawyer": NodeType.AGENT,
    "doctor": NodeType.AGENT,
    "employee": NodeType.AGENT,
    "ceo": NodeType.AGENT,
    "researcher": NodeType.AGENT,
    "activist": NodeType.AGENT,
    "politician": NodeType.AGENT,
    # INSTITUTION
    "organization": NodeType.INSTITUTION,
    "university": NodeType.INSTITUTION,
    "company": NodeType.INSTITUTION,
    "governmentagency": NodeType.INSTITUTION,
    "mediaoutlet": NodeType.INSTITUTION,
    "hospital": NodeType.INSTITUTION,
    "school": NodeType.INSTITUTION,
    "ngo": NodeType.INSTITUTION,
    "party": NodeType.INSTITUTION,
    # IDEA
    "idea": NodeType.IDEA,
    "policy": NodeType.IDEA,
    "narrative": NodeType.IDEA,
    "norm": NodeType.IDEA,
    "belief": NodeType.IDEA,
    # RESOURCE
    "resource": NodeType.RESOURCE,
    "market": NodeType.RESOURCE,
    "fund": NodeType.RESOURCE,
    "budget": NodeType.RESOURCE,
    # ENVIRONMENT
    "environment": NodeType.ENVIRONMENT,
    "platform": NodeType.ENVIRONMENT,
    "region": NodeType.ENVIRONMENT,
}

# Zep fact_type / edge names → EdgeType.  Checked case-insensitively.
_RELATION_TO_EDGE_TYPE: dict[str, EdgeType] = {
    # INFLUENCE
    "influence": EdgeType.INFLUENCE,
    "supports": EdgeType.INFLUENCE,
    "opposes": EdgeType.INFLUENCE,
    "endorses": EdgeType.INFLUENCE,
    "criticizes": EdgeType.INFLUENCE,
    "mentors": EdgeType.INFLUENCE,
    "advises": EdgeType.INFLUENCE,
    # INFORMATION
    "reports_on": EdgeType.INFORMATION,
    "comments_on": EdgeType.INFORMATION,
    "responds_to": EdgeType.INFORMATION,
    "cites": EdgeType.INFORMATION,
    "publishes": EdgeType.INFORMATION,
    "informs": EdgeType.INFORMATION,
    # RESOURCE_FLOW
    "funds": EdgeType.RESOURCE_FLOW,
    "trades_with": EdgeType.RESOURCE_FLOW,
    "supplies": EdgeType.RESOURCE_FLOW,
    "invests_in": EdgeType.RESOURCE_FLOW,
    "pays": EdgeType.RESOURCE_FLOW,
    # MEMBERSHIP
    "works_for": EdgeType.MEMBERSHIP,
    "studies_at": EdgeType.MEMBERSHIP,
    "affiliated_with": EdgeType.MEMBERSHIP,
    "member_of": EdgeType.MEMBERSHIP,
    "belongs_to": EdgeType.MEMBERSHIP,
    "represents": EdgeType.MEMBERSHIP,
    # CONFLICT
    "competes_with": EdgeType.CONFLICT,
    "sues": EdgeType.CONFLICT,
    "opposes_policy": EdgeType.CONFLICT,
    "conflicts_with": EdgeType.CONFLICT,
    # COOPERATION
    "collaborates_with": EdgeType.COOPERATION,
    "partners_with": EdgeType.COOPERATION,
    "allies_with": EdgeType.COOPERATION,
    "cooperates_with": EdgeType.COOPERATION,
}


def _stable_id(prefix: str, source: str) -> str:
    """Create a short deterministic ID from a source string."""
    return prefix + hashlib.md5(source.encode()).hexdigest()[:10]


def _classify_node_type(labels: list[str]) -> NodeType:
    """Determine NodeType from Zep node labels."""
    for label in labels:
        key = label.lower().replace(" ", "").replace("_", "")
        if key in _LABEL_TO_NODE_TYPE:
            return _LABEL_TO_NODE_TYPE[key]
    return NodeType.AGENT  # default fallback


def _classify_edge_type(fact_type: str, edge_name: str) -> EdgeType:
    """Determine EdgeType from Zep edge fact_type or name."""
    for raw in (fact_type, edge_name):
        key = raw.lower().replace(" ", "_")
        if key in _RELATION_TO_EDGE_TYPE:
            return _RELATION_TO_EDGE_TYPE[key]
    return EdgeType.INFLUENCE  # default fallback


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class DynamicsInitializer:
    """Converts Zep graph data into a DynamicsGraph."""

    def initialize(
        self,
        graph_data: dict[str, Any],
        ontology: dict[str, Any] | None = None,
    ) -> DynamicsGraph:
        """Build a DynamicsGraph from Zep graph data.

        Args:
            graph_data: Output of ``GraphBuilderService.get_graph_data()``.
                        Must contain ``nodes`` and ``edges`` lists.
            ontology:   Optional ontology definition (from ``OntologyGenerator``).
                        Used to improve type classification and generate richer
                        initial states.

        Returns:
            A populated ``DynamicsGraph`` ready for simulation.
        """
        dg = DynamicsGraph()
        uuid_to_nid: dict[str, str] = {}

        # --- nodes ---
        for zep_node in graph_data.get("nodes", []):
            zep_uuid = zep_node["uuid"]
            labels = zep_node.get("labels", [])
            name = zep_node.get("name", zep_uuid)

            node_type = _classify_node_type(labels)
            nid = _stable_id("n_", zep_uuid)
            uuid_to_nid[zep_uuid] = nid

            # Infer institution_id from labels for organization types
            institution_id = nid if node_type == NodeType.INSTITUTION else None

            state = self._initial_state(node_type, zep_node.get("attributes", {}))

            node = GraphNode(
                node_id=nid,
                node_type=node_type,
                label=name,
                state=state,
                institution_id=institution_id,
                source_entity_id=zep_uuid,
                metadata={"labels": labels, "summary": zep_node.get("summary", "")},
            )
            dg.add_node(node)

        # --- edges ---
        for zep_edge in graph_data.get("edges", []):
            src_uuid = zep_edge.get("source_node_uuid")
            tgt_uuid = zep_edge.get("target_node_uuid")

            src_nid = uuid_to_nid.get(src_uuid)
            tgt_nid = uuid_to_nid.get(tgt_uuid)
            if src_nid is None or tgt_nid is None:
                continue  # skip dangling edges

            fact_type = zep_edge.get("fact_type", "")
            edge_name = zep_edge.get("name", "")
            edge_type = _classify_edge_type(fact_type, edge_name)
            eid = _stable_id("e_", zep_edge.get("uuid", f"{src_uuid}_{tgt_uuid}"))

            edge = GraphEdge(
                edge_id=eid,
                source_id=src_nid,
                target_id=tgt_nid,
                edge_type=edge_type,
                weight=1.0,
                metadata={"fact": zep_edge.get("fact", ""), "fact_type": fact_type},
            )
            dg.add_edge(edge)

        # --- membership edges: connect agents to their institutions ---
        self._add_membership_edges(dg, graph_data)

        return dg

    def suggest_templates(self, graph: DynamicsGraph) -> list[str]:
        """Suggest dynamical templates based on graph composition.

        Returns a list of template names (keys into ``TEMPLATE_REGISTRY``).
        """
        suggestions: list[str] = []
        edge_types = {e.edge_type for e in graph._edges.values()}
        node_types = {n.node_type for n in graph._nodes.values()}

        # Always include diffusion — it's the baseline spreading model
        suggestions.append("diffusion")

        # Opinion dynamics if there are agents
        if NodeType.AGENT in node_types:
            suggestions.append("opinion")

        # Evolutionary if there are competing ideas
        idea_count = len(graph.nodes_by_type(NodeType.IDEA))
        if idea_count >= 2:
            suggestions.append("evolutionary")

        # Resource flow if resource edges exist
        if EdgeType.RESOURCE_FLOW in edge_types or NodeType.RESOURCE in node_types:
            suggestions.append("resource")

        # Feedback if there are loops or cooperation/conflict edges
        has_loops = len(graph.get_feedback_loops(max_length=4)) > 0
        if has_loops or EdgeType.COOPERATION in edge_types or EdgeType.CONFLICT in edge_types:
            suggestions.append("feedback")

        return suggestions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _initial_state(node_type: NodeType, attributes: dict[str, Any]) -> NodeState:
        """Assign empirical-prior initial state values based on node type."""
        defaults: dict[str, Any] = {
            NodeType.AGENT: dict(
                resources=1.0, stability=1.0, influence=0.5,
                energy=1.0, mutation_rate=0.01,
            ),
            NodeType.INSTITUTION: dict(
                resources=5.0, stability=3.0, influence=2.0,
                energy=2.0, mutation_rate=0.001,
            ),
            NodeType.IDEA: dict(
                resources=0.0, stability=0.5, influence=0.0,
                energy=1.0, mutation_rate=0.05,
            ),
            NodeType.RESOURCE: dict(
                resources=10.0, stability=1.0, influence=0.0,
                energy=5.0, mutation_rate=0.0,
            ),
            NodeType.ENVIRONMENT: dict(
                resources=0.0, stability=5.0, influence=1.0,
                energy=1.0, mutation_rate=0.0,
            ),
        }
        vals = defaults.get(node_type, {})
        return NodeState(**vals)

    def _add_membership_edges(
        self, dg: DynamicsGraph, graph_data: dict[str, Any]
    ) -> None:
        """Infer MEMBERSHIP edges from Zep 'works_for'/'studies_at'/etc.

        If a Zep edge has a membership-like fact_type and connects an
        AGENT to an INSTITUTION, also assign the agent's institution_id.
        """
        membership_keys = {
            "works_for", "studies_at", "affiliated_with",
            "member_of", "belongs_to",
        }
        for edge in dg._edges.values():
            if edge.edge_type != EdgeType.MEMBERSHIP:
                continue
            src_node = dg.get_node(edge.source_id)
            tgt_node = dg.get_node(edge.target_id)
            if src_node and tgt_node:
                if (
                    src_node.node_type == NodeType.AGENT
                    and tgt_node.node_type == NodeType.INSTITUTION
                    and src_node.institution_id is None
                ):
                    dg.assign_institution(src_node.node_id, tgt_node.node_id)
