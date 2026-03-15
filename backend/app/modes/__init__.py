"""Simulation mode registry."""

from .base import SimulationMode
from .custom import CustomMode
from .ecological_systems import EcologicalSystemsMode
from .ecosystem import EcosystemMode
from .knowledge_ecosystems import KnowledgeEcosystemsMode
from .market_dynamics import MarketDynamicsMode
from .memetic_physics import MemeticPhysicsMode
from .public_discourse import PublicDiscourseMode
from .synthetic_civ import SyntheticCivMode

MODE_REGISTRY: dict[str, type[SimulationMode]] = {
    "custom": CustomMode,
    "synthetic_civ": SyntheticCivMode,
    "ecosystem": EcosystemMode,
    "memetic_physics": MemeticPhysicsMode,
    "market_dynamics": MarketDynamicsMode,
    "public_discourse": PublicDiscourseMode,
    "knowledge_ecosystems": KnowledgeEcosystemsMode,
    "ecological_systems": EcologicalSystemsMode,
}

__all__ = [
    "SimulationMode",
    "MODE_REGISTRY",
    "CustomMode",
    "SyntheticCivMode",
    "EcosystemMode",
    "MemeticPhysicsMode",
    "MarketDynamicsMode",
    "PublicDiscourseMode",
    "KnowledgeEcosystemsMode",
    "EcologicalSystemsMode",
]
