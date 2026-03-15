"""
Abstract base class for all dynamical equation templates.

Every template implements a single ``update()`` method that mutates
graph state in place for one timestep.  Templates declare what node
and edge types they require so the engine can validate compatibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ...dynamics.models import EdgeType, NodeType
from ...dynamics.graph import DynamicsGraph


@dataclass
class ParameterSpec:
    """Specification for a single tunable parameter."""
    default: float
    min_val: float
    max_val: float
    description: str = ""


class DynamicsTemplate(ABC):
    """Base class for all dynamical equation templates.

    Subclasses must set the class-level attributes and implement
    ``update()``.
    """

    name: str = ""
    description: str = ""
    required_node_types: list[NodeType] = []
    required_edge_types: list[EdgeType] = []
    parameters: dict[str, ParameterSpec] = {}

    @abstractmethod
    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        """Apply one timestep of dynamics.  Mutates *graph* state in place."""
        ...

    def get_empirical_priors(self) -> dict[str, float]:
        """Return default parameter values from literature."""
        return {k: v.default for k, v in self.parameters.items()}

    def validate_params(self, params: dict[str, float]) -> dict[str, float]:
        """Fill in missing params with defaults and clamp to valid range."""
        result: dict[str, float] = {}
        for name, spec in self.parameters.items():
            val = params.get(name, spec.default)
            val = max(spec.min_val, min(spec.max_val, val))
            result[name] = val
        return result
