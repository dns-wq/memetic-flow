"""Custom mode — passthrough for manual template selection."""

from ..dynamics import DynamicsGraph
from .base import SimulationMode


class CustomMode(SimulationMode):
    name = "custom"
    description = "Manual template selection with full parameter control."
    icon = "wrench"
    required_templates = []
    optional_templates = ["diffusion", "opinion", "evolutionary", "resource", "feedback"]
    visualization_preset = "force"
    metrics_focus = []
    suggested_for = []

    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        return base_graph
