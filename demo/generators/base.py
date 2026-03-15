"""
Base class for demo scenario generators.

Each generator creates a synthetic typed graph, configures a mode,
runs the simulation engine, and saves outputs as JSON bundles.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from backend.app.dynamics import DynamicsGraph, GraphEdge, GraphNode, NodeState
from backend.app.dynamics import EdgeType, NodeType
from backend.app.engine.runner import SimulationEngine
from backend.app.engine.templates import TEMPLATE_REGISTRY
from backend.app.metrics.collectors import MetricsCollector
from backend.app.modes import MODE_REGISTRY


class DemoGenerator(ABC):
    """Base class for demo scenario generators."""

    name: str = ""
    description: str = ""
    mode_name: str = ""
    steps: int = 200
    seed: int = 42

    @abstractmethod
    def build_graph(self, rng: np.random.Generator) -> DynamicsGraph:
        """Create the synthetic initial graph for this scenario."""
        ...

    # Override in subclasses to merge custom params over mode defaults
    param_overrides: dict[str, dict[str, float]] = {}

    def post_init(self, graph: DynamicsGraph) -> None:
        """Adjust graph state after mode initialization.

        Override this to restore values that the mode's initialize_graph
        may have overwritten (e.g. idea energies, species populations).
        """

    def generate(self, output_dir: str | Path) -> dict[str, Any]:
        """Run the full generation pipeline and save outputs."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        rng = np.random.default_rng(self.seed)

        # Build graph
        graph = self.build_graph(rng)

        # Apply mode initialization
        mode_cls = MODE_REGISTRY[self.mode_name]
        mode = mode_cls()
        graph = mode.initialize_graph(graph)

        # Allow subclasses to adjust state after mode initialization
        self.post_init(graph)

        # Create template instances
        template_names = mode.get_templates()
        templates = [TEMPLATE_REGISTRY[t]() for t in template_names]
        params = mode.get_params()
        # Merge any demo-specific parameter overrides
        for tname, overrides in self.param_overrides.items():
            params.setdefault(tname, {}).update(overrides)

        # Create engine
        collector = MetricsCollector()
        engine = SimulationEngine(
            graph=graph,
            templates=templates,
            params=params,
            seed=self.seed,
            metrics_collector=collector,
        )

        # Save initial snapshot
        initial_snap = graph.snapshot()

        # Run simulation, collecting events from mode hook
        all_events: list[dict[str, Any]] = []
        snapshots: list[dict[str, Any]] = []

        def on_step(step_num: int, snap):
            # Run mode post-step hook
            events = mode.post_step_hook(graph, step_num)
            all_events.extend(events)

        engine.run(self.steps, callback=on_step)

        # Collect all snapshots from graph history
        for snap in graph.history:
            snapshots.append(_snapshot_to_dict(snap))

        # Collect metric time series
        metrics_series: dict[str, list[float]] = {}
        for snap in graph.history:
            for key, val in snap.metrics.items():
                metrics_series.setdefault(key, []).append(val)

        # Build metadata
        metadata = {
            "name": self.name,
            "description": self.description,
            "mode": self.mode_name,
            "templates": template_names,
            "params": params,
            "steps": self.steps,
            "seed": self.seed,
            "num_nodes": len(graph.nodes),
            "num_edges": len(graph.edges),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Save files
        _save_json(output_dir / "metadata.json", metadata)
        _save_json(output_dir / "initial_graph.json", _snapshot_to_dict(initial_snap))
        _save_json(output_dir / "metrics.json", metrics_series)
        _save_json(output_dir / "events.json", all_events)

        # Save snapshots — can be large, compress by saving every Nth
        # For the demo we save every 5th snapshot to keep file sizes manageable
        sampled = snapshots[::5]
        if snapshots and sampled[-1] != snapshots[-1]:
            sampled.append(snapshots[-1])
        _save_json(output_dir / "snapshots.json", sampled)

        print(f"  Generated {self.name}: {len(snapshots)} steps, "
              f"{len(all_events)} events, {len(graph.nodes)} nodes, "
              f"{len(graph.edges)} edges")

        return metadata

    # --- Helpers for subclasses ---

    @staticmethod
    def _deterministic_id(label: str) -> str:
        """Generate a deterministic node ID from the label."""
        import hashlib
        return hashlib.md5(label.encode()).hexdigest()[:12]

    @classmethod
    def make_agent(cls, label: str, rng: np.random.Generator,
                   energy: float = 1.0, resources: float = 1.0,
                   influence: float = 0.5,
                   ideology: list[float] | None = None,
                   node_id: str | None = None,
                   metadata: dict[str, Any] | None = None) -> GraphNode:
        ideo = ideology if ideology is not None else [rng.uniform(0, 1), rng.uniform(0, 1)]
        return GraphNode(
            node_id=node_id or cls._deterministic_id(label),
            node_type=NodeType.AGENT,
            label=label,
            state=NodeState(
                energy=energy,
                resources=resources,
                influence=influence,
                ideological_position=ideo,
            ),
            metadata=metadata or {},
        )

    @classmethod
    def make_idea(cls, label: str, energy: float = 1.0,
                  stability: float = 1.0,
                  node_id: str | None = None,
                  metadata: dict[str, Any] | None = None) -> GraphNode:
        return GraphNode(
            node_id=node_id or cls._deterministic_id(label),
            node_type=NodeType.IDEA,
            label=label,
            state=NodeState(energy=energy, stability=stability),
            metadata=metadata or {},
        )

    @classmethod
    def make_institution(cls, label: str, resources: float = 2.0,
                         node_id: str | None = None,
                         metadata: dict[str, Any] | None = None) -> GraphNode:
        return GraphNode(
            node_id=node_id or cls._deterministic_id(label),
            node_type=NodeType.INSTITUTION,
            label=label,
            state=NodeState(
                resources=resources, stability=2.0,
                influence=1.5, energy=2.0,
            ),
            metadata=metadata or {},
        )

    @classmethod
    def make_resource(cls, label: str, resources: float = 5.0,
                      node_id: str | None = None,
                      metadata: dict[str, Any] | None = None) -> GraphNode:
        return GraphNode(
            node_id=node_id or cls._deterministic_id(label),
            node_type=NodeType.RESOURCE,
            label=label,
            state=NodeState(resources=resources, energy=1.0),
            metadata=metadata or {},
        )

    @classmethod
    def make_environment(cls, label: str, resources: float = 10.0,
                         stability: float = 2.0,
                         node_id: str | None = None,
                         metadata: dict[str, Any] | None = None) -> GraphNode:
        return GraphNode(
            node_id=node_id or cls._deterministic_id(label),
            node_type=NodeType.ENVIRONMENT,
            label=label,
            state=NodeState(resources=resources, stability=stability, energy=1.0),
            metadata=metadata or {},
        )

    @staticmethod
    def connect(source: GraphNode, target: GraphNode,
                edge_type: EdgeType, weight: float = 1.0,
                transfer_rate: float = 0.1) -> GraphEdge:
        return GraphEdge(
            source_id=source.node_id,
            target_id=target.node_id,
            edge_type=edge_type,
            weight=weight,
            transfer_rate=transfer_rate,
        )


def _snapshot_to_dict(snap) -> dict[str, Any]:
    """Convert a GraphSnapshot to a JSON-serializable dict."""
    return {
        "timestep": snap.timestep,
        "nodes": [
            {
                "node_id": n.node_id,
                "node_type": n.node_type.value if hasattr(n.node_type, 'value') else n.node_type,
                "label": n.label,
                "state": {
                    "energy": n.state.energy,
                    "resources": n.state.resources,
                    "influence": n.state.influence,
                    "stability": n.state.stability,
                    "ideological_position": n.state.ideological_position,
                    "mutation_rate": n.state.mutation_rate,
                },
                "institution_id": n.institution_id,
                "metadata": n.metadata,
            }
            for n in snap.nodes.values()
        ],
        "edges": [
            {
                "edge_id": e.edge_id,
                "source_id": e.source_id,
                "target_id": e.target_id,
                "edge_type": e.edge_type.value if hasattr(e.edge_type, 'value') else e.edge_type,
                "weight": e.weight,
                "transfer_rate": e.transfer_rate,
            }
            for e in snap.edges.values()
        ],
        "metrics": snap.metrics,
    }


def _save_json(path: Path, data: Any) -> None:
    """Write data as JSON with compact formatting."""
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"), default=str)
