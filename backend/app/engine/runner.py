"""
Simulation engine orchestrator.

SimulationEngine owns a DynamicsGraph, a list of templates, and a
metrics collector.  Each ``step()`` call applies all templates
sequentially, computes metrics, and saves a snapshot.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from ..dynamics.graph import DynamicsGraph
from ..dynamics.models import GraphSnapshot
from .templates.base import DynamicsTemplate


class SimulationEngine:
    """Orchestrates template-based dynamical simulation."""

    def __init__(
        self,
        graph: DynamicsGraph,
        templates: list[DynamicsTemplate],
        params: dict[str, dict[str, float]] | None = None,
        seed: int = 42,
        metrics_collector: Any | None = None,
    ) -> None:
        self.graph = graph
        self.templates = list(templates)
        self._params: dict[str, dict[str, float]] = params or {}
        self.rng = np.random.default_rng(seed)
        self._metrics_collector = metrics_collector
        self._running = False

    # ------------------------------------------------------------------
    # Parameter management
    # ------------------------------------------------------------------

    def set_params(self, template_name: str, params: dict[str, float]) -> None:
        self._params[template_name] = params

    def get_params(self, template_name: str) -> dict[str, float]:
        return self._params.get(template_name, {})

    def get_all_params(self) -> dict[str, dict[str, float]]:
        """Return all current params, filling defaults from templates."""
        result: dict[str, dict[str, float]] = {}
        for t in self.templates:
            raw = self._params.get(t.name, {})
            result[t.name] = t.validate_params(raw)
        return result

    # ------------------------------------------------------------------
    # Simulation execution
    # ------------------------------------------------------------------

    def step(self) -> GraphSnapshot:
        """Run one timestep: apply all templates, compute metrics, snapshot."""
        self.graph.advance_timestep()

        for template in self.templates:
            raw_params = self._params.get(template.name, {})
            validated = template.validate_params(raw_params)
            template.update(self.graph, validated, self.rng)

        # Compute metrics if collector is available
        snap = self.graph.snapshot()
        if self._metrics_collector is not None:
            snap.metrics = self._metrics_collector.compute(self.graph)

        self.graph.save_snapshot(snap)
        return snap

    def run(
        self,
        steps: int,
        callback: Callable[[int, GraphSnapshot], None] | None = None,
    ) -> list[GraphSnapshot]:
        """Run *steps* timesteps, returning all snapshots."""
        self._running = True
        snapshots: list[GraphSnapshot] = []

        for i in range(steps):
            if not self._running:
                break
            snap = self.step()
            snapshots.append(snap)
            if callback is not None:
                callback(i + 1, snap)

        self._running = False
        return snapshots

    def stop(self) -> None:
        """Signal the engine to stop after the current step."""
        self._running = False

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    def add_template(self, template: DynamicsTemplate) -> None:
        if any(t.name == template.name for t in self.templates):
            raise ValueError(f"Template {template.name!r} already registered")
        self.templates.append(template)

    def remove_template(self, name: str) -> None:
        self.templates = [t for t in self.templates if t.name != name]
        self._params.pop(name, None)

    @property
    def template_names(self) -> list[str]:
        return [t.name for t in self.templates]
