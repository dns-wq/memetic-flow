"""
Civilization from Scratch demo scenario.

Mode: synthetic_civ
Templates: diffusion, opinion, resource, feedback

200 agents in 5 geographic clusters self-organize into institutions
and trade networks. The "wow" demo — watch society emerge from nothing.
"""

from __future__ import annotations

import numpy as np

from backend.app.dynamics import DynamicsGraph, EdgeType, NodeType
from .base import DemoGenerator

# Per-cluster specialization pools — each agent picks one at random
_CLUSTER_SPECS = {
    "River": [
        {"role": "Irrigation engineer", "goals": "Design canal networks to water the floodplain fields"},
        {"role": "Rice farmer", "goals": "Maximize grain yield through crop rotation"},
        {"role": "Fisherman", "goals": "Supply protein from river catches and fish traps"},
        {"role": "Potter", "goals": "Craft storage vessels for surplus grain"},
        {"role": "Reed weaver", "goals": "Build boats and baskets from riverside reeds"},
        {"role": "Flood watcher", "goals": "Predict seasonal floods to protect settlements"},
        {"role": "Herbalist", "goals": "Gather medicinal plants from the river marshes"},
        {"role": "Ferry operator", "goals": "Control river crossings and collect tolls"},
        {"role": "Grain trader", "goals": "Broker surplus harvests to neighboring clusters"},
        {"role": "Midwife", "goals": "Ensure healthy births and growing population"},
    ],
    "Mountain": [
        {"role": "Copper miner", "goals": "Extract ore from highland shafts"},
        {"role": "Stonecutter", "goals": "Quarry and shape building blocks for fortifications"},
        {"role": "Goat herder", "goals": "Raise livestock on alpine pastures for meat and wool"},
        {"role": "Lookout sentry", "goals": "Guard mountain passes against raiders"},
        {"role": "Trail builder", "goals": "Maintain footpaths linking highland villages"},
        {"role": "Charcoal burner", "goals": "Produce fuel for smelting and warmth"},
        {"role": "Blacksmith", "goals": "Forge tools, weapons, and trade goods from metal"},
        {"role": "Mountain guide", "goals": "Lead caravans safely through treacherous passes"},
    ],
    "Coastal": [
        {"role": "Shipwright", "goals": "Build and repair seagoing vessels"},
        {"role": "Deep-sea fisher", "goals": "Harvest ocean fish and shellfish"},
        {"role": "Salt harvester", "goals": "Evaporate seawater to produce valuable salt"},
        {"role": "Harbor master", "goals": "Organize docking, loading, and trade logistics"},
        {"role": "Navigator", "goals": "Chart sea routes and read tides and stars"},
        {"role": "Pearl diver", "goals": "Retrieve pearls and coral for luxury trade"},
        {"role": "Net mender", "goals": "Maintain fishing gear for the fleet"},
        {"role": "Tide watcher", "goals": "Predict tidal patterns for safe harbor entry"},
        {"role": "Sail maker", "goals": "Weave and stitch canvas for the trading fleet"},
    ],
    "Desert": [
        {"role": "Caravan leader", "goals": "Guide trade convoys between oases"},
        {"role": "Well digger", "goals": "Find and maintain water sources in the arid waste"},
        {"role": "Camel breeder", "goals": "Raise pack animals for desert transport"},
        {"role": "Sand navigator", "goals": "Read dune patterns and star positions for wayfinding"},
        {"role": "Date farmer", "goals": "Cultivate palm groves around oasis springs"},
        {"role": "Leather tanner", "goals": "Process hides into goods for trade and shelter"},
        {"role": "Storyteller", "goals": "Preserve oral history and entertain at camps"},
        {"role": "Scout", "goals": "Patrol trade routes and report threats or opportunities"},
    ],
    "Central": [
        {"role": "Woodcutter", "goals": "Harvest timber sustainably from the forest"},
        {"role": "Herb gatherer", "goals": "Collect medicinal and culinary plants"},
        {"role": "Hunter", "goals": "Track game and supply meat to the commune"},
        {"role": "Beekeeper", "goals": "Tend forest hives for honey and wax"},
        {"role": "Charcoal maker", "goals": "Convert wood to fuel for trade with other clusters"},
        {"role": "Carpenter", "goals": "Build shelters, fences, and market stalls"},
        {"role": "Mushroom forager", "goals": "Identify and harvest edible fungi"},
        {"role": "Trapper", "goals": "Set snares for furs valued in highland and coastal trade"},
        {"role": "Path keeper", "goals": "Clear and mark trails through dense forest"},
        {"role": "Market organizer", "goals": "Host seasonal fairs where all clusters meet to trade"},
    ],
}


class CivilizationFromScratchDemo(DemoGenerator):
    name = "civilization_from_scratch"
    description = (
        "Watch institutions, norms, and trade emerge from nothing. "
        "200 agents begin as survival-driven actors and self-organize "
        "into a functioning society."
    )
    mode_name = "synthetic_civ"
    steps = 400
    seed = 1776

    def build_graph(self, rng: np.random.Generator) -> DynamicsGraph:
        graph = DynamicsGraph()
        agents = []

        # --- 200 agents in 5 geographic clusters ---
        cluster_centers = [
            (0.15, 0.15),   # River Valley
            (0.85, 0.15),   # Mountain Kingdom
            (0.15, 0.85),   # Coastal Haven
            (0.85, 0.85),   # Desert Outpost
            (0.50, 0.50),   # Central Crossroads
        ]
        cluster_names = ["River", "Mountain", "Coastal", "Desert", "Central"]
        cluster_sizes = [45, 35, 40, 30, 50]

        for ci, (cx, cy) in enumerate(cluster_centers):
            specs = _CLUSTER_SPECS[cluster_names[ci]]
            for i in range(cluster_sizes[ci]):
                spec = specs[i % len(specs)]
                a = self.make_agent(
                    f"{cluster_names[ci]}-{i+1}", rng,
                    energy=1.0 + rng.uniform(0, 0.8),
                    resources=0.8 + rng.uniform(0, 1.5),
                    influence=0.2 + rng.uniform(0, 0.5),
                    ideology=[
                        cx + rng.normal(0, 0.06),
                        cy + rng.normal(0, 0.06),
                    ],
                    metadata=spec,
                )
                agents.append(a)
                graph.add_node(a)

        # --- Environments ---
        envs = [
            self.make_environment("Fertile River Basin", resources=15.0, stability=3.0,
                                  metadata={"description": "Rich alluvial plains fed by seasonal floods"}),
            self.make_environment("Mountain Peaks", resources=8.0, stability=2.5,
                                  metadata={"description": "Rugged highlands with steep passes and alpine meadows"}),
            self.make_environment("Coastal Waters", resources=12.0, stability=2.5,
                                  metadata={"description": "Sheltered coastline with tidal estuaries and natural harbors"}),
            self.make_environment("Desert Oasis", resources=5.0, stability=1.5,
                                  metadata={"description": "Arid expanse punctuated by life-giving oases and wadis"}),
            self.make_environment("Crossroads Plateau", resources=10.0, stability=2.0,
                                  metadata={"description": "Temperate forested plateau where major trade paths converge"}),
        ]
        for env in envs:
            graph.add_node(env)

        # --- Resources ---
        resources = [
            self.make_resource("Food Supply", resources=10.0,
                               metadata={"description": "Fresh water from mountain springs, essential for settlement"}),
            self.make_resource("Building Materials", resources=8.0,
                               metadata={"description": "Timber, stone, and clay for constructing shelters and walls"}),
            self.make_resource("Trade Goods", resources=6.0,
                               metadata={"description": "Luxury items and exotic crafts valued across all regions"}),
            self.make_resource("Metal Ore", resources=5.0,
                               metadata={"description": "Iron and copper deposits used for tools and weapons"}),
            self.make_resource("Cloth and Textiles", resources=4.0,
                               metadata={"description": "Woven fabrics from wool and plant fibers for clothing and trade"}),
            self.make_resource("Medicinal Herbs", resources=3.0,
                               metadata={"description": "Rare plants with healing properties gathered from forest and field"}),
        ]
        for r in resources:
            graph.add_node(r)

        # --- Proto-norms and ideas ---
        ideas = [
            self.make_idea("Cooperative Farming", energy=1.5, stability=1.0,
                           metadata={"thesis": "Shared labor produces surplus for all",
                                     "counter": "Free riders undermine collective effort"}),
            self.make_idea("Property Rights", energy=1.0, stability=0.8,
                           metadata={"thesis": "Clear ownership incentivizes investment and stewardship",
                                     "counter": "Enclosure excludes the landless and deepens inequality"}),
            self.make_idea("Trade Networks", energy=1.2, stability=0.8,
                           metadata={"thesis": "Exchange spreads wealth and fosters mutual dependence",
                                     "counter": "Trade asymmetries let powerful actors exploit weaker partners"}),
            self.make_idea("Collective Defense", energy=1.0, stability=0.7,
                           metadata={"thesis": "United defense deters aggressors and protects all members",
                                     "counter": "Standing militias concentrate coercive power in few hands"}),
            self.make_idea("Knowledge Sharing", energy=0.8, stability=0.5,
                           metadata={"thesis": "Open knowledge accelerates innovation for the whole community",
                                     "counter": "Shared secrets erode the competitive edge of discoverers"}),
            self.make_idea("Apprenticeship System", energy=0.6, stability=0.5,
                           metadata={"thesis": "Mentorship preserves craft mastery across generations",
                                     "counter": "Guild gatekeeping restricts access and stifles new methods"}),
            self.make_idea("Dispute Resolution", energy=0.8, stability=0.6,
                           metadata={"thesis": "Neutral arbitration prevents feuds from spiraling into violence",
                                     "counter": "Formalized courts favor the eloquent and well-connected"}),
            self.make_idea("Resource Pooling", energy=0.7, stability=0.5,
                           metadata={"thesis": "Communal reserves buffer against famine and disaster",
                                     "counter": "Shared stores invite overconsumption and accounting disputes"}),
            self.make_idea("Seasonal Festivals", energy=0.5, stability=0.4,
                           metadata={"thesis": "Shared rituals strengthen social bonds and collective identity",
                                     "counter": "Mandatory celebrations impose conformity and waste scarce resources"}),
            self.make_idea("Navigation and Maps", energy=0.9, stability=0.6,
                           metadata={"thesis": "Charted routes open new lands and safer passage for all",
                                     "counter": "Map-holders monopolize exploration and territorial claims"}),
        ]
        for idea in ideas:
            graph.add_node(idea)

        # --- Intra-cluster edges: dense local cooperation ---
        offset = 0
        for ci, size in enumerate(cluster_sizes):
            cluster = agents[offset:offset + size]
            for i, a1 in enumerate(cluster):
                for j, a2 in enumerate(cluster):
                    if i >= j:
                        continue
                    # Higher probability = denser clusters
                    if rng.random() < 0.20:
                        w = 0.3 + rng.uniform(0, 0.5)
                        graph.add_edge(self.connect(
                            a1, a2, EdgeType.COOPERATION,
                            weight=w, transfer_rate=0.1,
                        ))
                        if rng.random() < 0.7:
                            graph.add_edge(self.connect(
                                a2, a1, EdgeType.COOPERATION,
                                weight=w * 0.8, transfer_rate=0.1,
                            ))
            offset += size

        # --- Inter-cluster bridges (sparse early trade contacts) ---
        offset_map = {}
        offset = 0
        for ci, size in enumerate(cluster_sizes):
            offset_map[ci] = (offset, offset + size)
            offset += size

        for ci in range(5):
            for cj in range(ci + 1, 5):
                s1, e1 = offset_map[ci]
                s2, e2 = offset_map[cj]
                c1 = agents[s1:e1]
                c2 = agents[s2:e2]
                # Central cluster gets more bridges
                num_bridges = rng.integers(2, 5) if 4 in (ci, cj) else rng.integers(1, 3)
                for _ in range(num_bridges):
                    a1 = rng.choice(c1)
                    a2 = rng.choice(c2)
                    graph.add_edge(self.connect(
                        a1, a2, EdgeType.INFLUENCE,
                        weight=0.15 + rng.uniform(0, 0.2),
                        transfer_rate=0.04,
                    ))

        # --- Agent-environment connections ---
        offset = 0
        for ci, size in enumerate(cluster_sizes):
            cluster = agents[offset:offset + size]
            for a in cluster:
                graph.add_edge(self.connect(
                    envs[ci], a, EdgeType.RESOURCE_FLOW,
                    weight=0.3 + rng.uniform(0, 0.3),
                    transfer_rate=0.08,
                ))
            offset += size

        # --- Agent-resource competition ---
        for a in agents:
            targets = rng.choice(resources, size=rng.integers(1, 3), replace=False)
            for r in targets:
                graph.add_edge(self.connect(
                    a, r, EdgeType.RESOURCE_FLOW,
                    weight=0.15 + rng.uniform(0, 0.2),
                    transfer_rate=0.05,
                ))

        # --- Early idea adoption (sparse) ---
        for a in agents:
            if rng.random() < 0.12:
                idea = rng.choice(ideas)
                graph.add_edge(self.connect(
                    a, idea, EdgeType.INFORMATION,
                    weight=0.2 + rng.uniform(0, 0.2),
                    transfer_rate=0.06,
                ))

        return graph
