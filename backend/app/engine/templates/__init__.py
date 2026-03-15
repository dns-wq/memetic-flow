"""Template equation families for the dynamical simulation engine."""

from .base import DynamicsTemplate, ParameterSpec
from .diffusion import DiffusionTemplate
from .opinion import OpinionTemplate
from .evolutionary import EvolutionaryTemplate
from .resource import ResourceTemplate
from .feedback import FeedbackTemplate
from .contagion import ContagionTemplate
from .game_theory import GameTheoryTemplate
from .network_evolution import NetworkEvolutionTemplate
from .memory_landscape import MemoryLandscapeTemplate

TEMPLATE_REGISTRY: dict[str, type[DynamicsTemplate]] = {
    "diffusion": DiffusionTemplate,
    "opinion": OpinionTemplate,
    "evolutionary": EvolutionaryTemplate,
    "resource": ResourceTemplate,
    "feedback": FeedbackTemplate,
    "contagion": ContagionTemplate,
    "game_theory": GameTheoryTemplate,
    "network_evolution": NetworkEvolutionTemplate,
    "memory_landscape": MemoryLandscapeTemplate,
}

__all__ = [
    "DynamicsTemplate",
    "ParameterSpec",
    "DiffusionTemplate",
    "OpinionTemplate",
    "EvolutionaryTemplate",
    "ResourceTemplate",
    "FeedbackTemplate",
    "ContagionTemplate",
    "GameTheoryTemplate",
    "NetworkEvolutionTemplate",
    "MemoryLandscapeTemplate",
    "TEMPLATE_REGISTRY",
]
