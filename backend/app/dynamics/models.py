"""
Typed graph data models for the dynamical simulation engine.

Defines node types, edge types, state vectors, and graph snapshots
that form the foundation for all template-based dynamics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the dynamics graph."""
    AGENT = "agent"
    INSTITUTION = "institution"
    IDEA = "idea"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"


class EdgeType(str, Enum):
    """Types of directed edges in the dynamics graph."""
    INFLUENCE = "influence"
    INFORMATION = "information"
    RESOURCE_FLOW = "resource_flow"
    MEMBERSHIP = "membership"
    CONFLICT = "conflict"
    COOPERATION = "cooperation"


class NodeState(BaseModel):
    """Extensible state vector attached to each node.

    All dynamical templates read from and write to these fields.
    The ``custom`` dict allows user-defined state variables without
    schema changes.
    """
    resources: float = 1.0
    stability: float = 1.0
    influence: float = 0.5
    ideological_position: list[float] = Field(default_factory=list)
    mutation_rate: float = 0.01
    energy: float = 1.0
    custom: dict[str, float] = Field(default_factory=dict)


class GraphNode(BaseModel):
    """A single node in the dynamics graph."""
    node_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    node_type: NodeType
    label: str
    state: NodeState = Field(default_factory=NodeState)
    institution_id: str | None = None
    source_entity_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """A directed, weighted edge in the dynamics graph."""
    edge_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    transfer_rate: float = 0.1
    decay_rate: float = 0.01
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphSnapshot(BaseModel):
    """Complete, immutable graph state at a single timestep.

    Snapshots are the unit of history — the engine saves one after
    every simulation step so the timeline can be replayed.
    """
    timestep: int
    nodes: dict[str, GraphNode]
    edges: dict[str, GraphEdge]
    institutions: dict[str, list[str]] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
