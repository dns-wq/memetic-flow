"""Template equation families for the dynamical simulation engine."""

from .base import DynamicsTemplate, ParameterSpec

# --- Core templates (Phases 1-7) ---
from .diffusion import DiffusionTemplate
from .opinion import OpinionTemplate
from .evolutionary import EvolutionaryTemplate
from .resource import ResourceTemplate
from .feedback import FeedbackTemplate

# --- Extended templates (Phase 16) ---
from .contagion import ContagionTemplate
from .game_theory import GameTheoryTemplate
from .network_evolution import NetworkEvolutionTemplate
from .memory_landscape import MemoryLandscapeTemplate

# --- Phase 9: Synthetic Civilizations ---
from .institutional import InstitutionalTemplate
from .norms import NormsTemplate
from .innovation import InnovationTemplate

# --- Phase 10: Digital Ecosystem ---
from .cognitive_ecology import CognitiveEcologyTemplate
from .attention import AttentionTemplate
from .cognitive_types import CognitiveTypesTemplate

# --- Phase 11: Memetic Physics ---
from .memetic_field import MemeticFieldTemplate
from .memetic_energy import MemeticEnergyTemplate
from .cultural_evolution import CulturalEvolutionTemplate

# --- Phase 12: Market Dynamics ---
from .market_clearing import MarketClearingTemplate
from .competitive import CompetitiveTemplate
from .supply_chain import SupplyChainTemplate

# --- Phase 13: Public Discourse ---
from .electoral import ElectoralTemplate
from .coalition import CoalitionTemplate
from .deliberation import DeliberationTemplate

# --- Phase 14: Knowledge Ecosystems ---
from .knowledge_production import KnowledgeProductionTemplate
from .peer_review import PeerReviewTemplate
from .paradigm import ParadigmTemplate

# --- Phase 15: Ecological Systems ---
from .population_ecology import PopulationEcologyTemplate
from .habitat import HabitatTemplate
from .ecosystem_services import EcosystemServicesTemplate

TEMPLATE_REGISTRY: dict[str, type[DynamicsTemplate]] = {
    # Core
    "diffusion": DiffusionTemplate,
    "opinion": OpinionTemplate,
    "evolutionary": EvolutionaryTemplate,
    "resource": ResourceTemplate,
    "feedback": FeedbackTemplate,
    # Extended
    "contagion": ContagionTemplate,
    "game_theory": GameTheoryTemplate,
    "network_evolution": NetworkEvolutionTemplate,
    "memory_landscape": MemoryLandscapeTemplate,
    # Phase 9: Synthetic Civilizations
    "institutional": InstitutionalTemplate,
    "norms": NormsTemplate,
    "innovation": InnovationTemplate,
    # Phase 10: Digital Ecosystem
    "cognitive_ecology": CognitiveEcologyTemplate,
    "attention": AttentionTemplate,
    "cognitive_types": CognitiveTypesTemplate,
    # Phase 11: Memetic Physics
    "memetic_field": MemeticFieldTemplate,
    "memetic_energy": MemeticEnergyTemplate,
    "cultural_evolution": CulturalEvolutionTemplate,
    # Phase 12: Market Dynamics
    "market_clearing": MarketClearingTemplate,
    "competitive": CompetitiveTemplate,
    "supply_chain": SupplyChainTemplate,
    # Phase 13: Public Discourse
    "electoral": ElectoralTemplate,
    "coalition": CoalitionTemplate,
    "deliberation": DeliberationTemplate,
    # Phase 14: Knowledge Ecosystems
    "knowledge_production": KnowledgeProductionTemplate,
    "peer_review": PeerReviewTemplate,
    "paradigm": ParadigmTemplate,
    # Phase 15: Ecological Systems
    "population_ecology": PopulationEcologyTemplate,
    "habitat": HabitatTemplate,
    "ecosystem_services": EcosystemServicesTemplate,
}

__all__ = [
    "DynamicsTemplate",
    "ParameterSpec",
    "TEMPLATE_REGISTRY",
    # Core
    "DiffusionTemplate",
    "OpinionTemplate",
    "EvolutionaryTemplate",
    "ResourceTemplate",
    "FeedbackTemplate",
    # Extended
    "ContagionTemplate",
    "GameTheoryTemplate",
    "NetworkEvolutionTemplate",
    "MemoryLandscapeTemplate",
    # Phase 9
    "InstitutionalTemplate",
    "NormsTemplate",
    "InnovationTemplate",
    # Phase 10
    "CognitiveEcologyTemplate",
    "AttentionTemplate",
    "CognitiveTypesTemplate",
    # Phase 11
    "MemeticFieldTemplate",
    "MemeticEnergyTemplate",
    "CulturalEvolutionTemplate",
    # Phase 12
    "MarketClearingTemplate",
    "CompetitiveTemplate",
    "SupplyChainTemplate",
    # Phase 13
    "ElectoralTemplate",
    "CoalitionTemplate",
    "DeliberationTemplate",
    # Phase 14
    "KnowledgeProductionTemplate",
    "PeerReviewTemplate",
    "ParadigmTemplate",
    # Phase 15
    "PopulationEcologyTemplate",
    "HabitatTemplate",
    "EcosystemServicesTemplate",
]
