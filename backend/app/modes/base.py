"""
Base class for simulation modes.

A mode bundles specific templates, node types, visualization presets,
and metrics into a curated experience.  Each mode is a configuration
profile over the unified engine — not a separate codebase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..dynamics import DynamicsGraph, NodeType, EdgeType


class SimulationMode(ABC):
    """Abstract base class for all simulation modes."""

    # --- Metadata (override in subclasses) ---
    name: str = ""
    description: str = ""
    icon: str = ""

    # --- Template configuration ---
    required_templates: list[str] = []
    optional_templates: list[str] = []
    default_params: dict[str, dict[str, float]] = {}

    # --- Type configuration ---
    node_type_config: dict[NodeType, dict[str, Any]] = {}
    edge_type_config: dict[EdgeType, dict[str, Any]] = {}

    # --- Visualization ---
    visualization_preset: str = "force"
    metrics_focus: list[str] = []

    # --- Discovery ---
    suggested_for: list[str] = []

    def configure(self, **kwargs: Any) -> None:
        """Apply runtime configuration to this mode.

        Called by the engine before simulation starts.  Subclasses can
        override to accept custom parameters; the default is a no-op.
        """

    def get_templates(self) -> list[str]:
        """Return the full list of templates this mode activates."""
        return list(self.required_templates)

    def get_params(self) -> dict[str, dict[str, float]]:
        """Return default parameter overrides for this mode."""
        return dict(self.default_params)

    @abstractmethod
    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        """Apply mode-specific initialization logic to the graph.

        Called after ``DynamicsInitializer.initialize()`` has built the
        base typed graph.  Modes can add synthetic nodes, adjust initial
        state values, or restructure edges.
        """
        ...

    def post_step_hook(self, graph: DynamicsGraph, timestep: int) -> list[dict[str, Any]]:
        """Mode-specific logic after each simulation step.

        Returns a (possibly empty) list of event dicts to surface in
        the UI (e.g. "Institution X formed at step 42").
        """
        return []

    def to_dict(self) -> dict[str, Any]:
        """Serialize mode metadata for the API."""
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "required_templates": self.required_templates,
            "optional_templates": self.optional_templates,
            "default_params": self.default_params,
            "visualization_preset": self.visualization_preset,
            "metrics_focus": self.metrics_focus,
            "suggested_for": self.suggested_for,
        }
