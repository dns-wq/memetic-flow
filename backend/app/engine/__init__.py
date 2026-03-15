"""Dynamical simulation engine with template-based update rules."""

from .runner import SimulationEngine
from .templates import TEMPLATE_REGISTRY

__all__ = ["SimulationEngine", "TEMPLATE_REGISTRY"]
