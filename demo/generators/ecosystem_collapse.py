"""
Ecosystem Collapse demo scenario.

Mode: ecological_systems
Templates: resource, evolutionary, feedback

120+ species across 6 habitats forming a rich food web.
Environmental stressors gradually degrade habitats, triggering
cascading species endangerment and tipping point events.
"""

from __future__ import annotations

import numpy as np

from backend.app.dynamics import DynamicsGraph, EdgeType, NodeType
from .base import DemoGenerator

# Species that should start vulnerable (low energy, triggering endangerment events)
_VULNERABLE_SPECIES = {
    "Monarch Butterflies", "Sea Turtles", "Coral Polyps",
    "Orca", "Tiger", "Harpy Eagle",
}
# Resources that should start under stress
_STRESSED_RESOURCES = {"Freshwater", "Soil"}


class EcosystemCollapseDemo(DemoGenerator):
    name = "ecosystem_collapse"
    description = (
        "Watch an ecosystem approach tipping points under stress. "
        "120+ species compete, habitats degrade, and cascading "
        "collapse reveals the fragility of complex systems."
    )
    mode_name = "ecological_systems"
    steps = 400
    seed = 1859

    def post_init(self, graph: DynamicsGraph) -> None:
        """Make vulnerable species and stressed resources more fragile."""
        for node in graph.nodes_by_type(NodeType.AGENT):
            if node.label in _VULNERABLE_SPECIES:
                # Below the 0.1 threshold for species_endangered events
                graph.update_node_state(node.node_id, energy=0.05, resources=0.2)
        for node in graph.nodes_by_type(NodeType.RESOURCE):
            if node.label in _STRESSED_RESOURCES:
                # Below thresholds for habitat_collapse (resources<1.0 AND stability<1.0)
                graph.update_node_state(node.node_id, resources=0.8, stability=0.5)

    def build_graph(self, rng: np.random.Generator) -> DynamicsGraph:
        graph = DynamicsGraph()

        # --- 6 Habitats (Environment nodes) ---
        habitats = [
            self.make_environment("Tropical Rainforest", resources=15.0, stability=3.0, metadata={"description": "Dense canopy with highest biodiversity on Earth"}),
            self.make_environment("Coral Reef", resources=12.0, stability=2.5, metadata={"description": "Underwater limestone structures built by coral colonies, supporting vast marine life"}),
            self.make_environment("Grassland Savanna", resources=10.0, stability=2.0, metadata={"description": "Open grassland with scattered trees, shaped by seasonal rainfall and grazing"}),
            self.make_environment("Freshwater Lake", resources=8.0, stability=2.0, metadata={"description": "Inland body of standing freshwater sustaining fish, amphibians, and waterbirds"}),
            self.make_environment("Mountain Forest", resources=7.0, stability=2.5, metadata={"description": "High-altitude woodland with cool temperatures and altitude-stratified species"}),
            self.make_environment("Mangrove Estuary", resources=9.0, stability=1.8, metadata={"description": "Coastal wetland where salt-tolerant trees buffer shorelines and nurse juvenile marine species"}),
        ]
        for h in habitats:
            graph.add_node(h)

        # --- Species organized by trophic level ---
        all_species = []

        # Primary producers (20 species — foundation of food web)
        producers = []
        producer_specs = [
            ("Phytoplankton", {"role": "Primary producer", "description": "Microscopic algae producing most of the ocean's oxygen"}),
            ("Tropical Trees", {"role": "Primary producer", "description": "Tall broadleaf trees forming the rainforest canopy"}),
            ("Seagrass", {"role": "Primary producer", "description": "Underwater flowering plants stabilizing coastal sediments"}),
            ("Savanna Grass", {"role": "Primary producer", "description": "Fire-adapted grasses dominating open tropical plains"}),
            ("Mountain Ferns", {"role": "Primary producer", "description": "Shade-tolerant ferns carpeting the forest understory"}),
            ("Algae", {"role": "Primary producer", "description": "Simple aquatic photosynthesizers found in freshwater and marine systems"}),
            ("Mangrove Trees", {"role": "Primary producer", "description": "Salt-tolerant trees with aerial roots anchoring coastal ecosystems"}),
            ("Kelp Forest", {"role": "Primary producer", "description": "Giant brown algae forming towering underwater forests"}),
            ("Wildflowers", {"role": "Primary producer", "description": "Diverse flowering plants providing nectar and pollen for pollinators"}),
            ("Bamboo", {"role": "Primary producer", "description": "Fast-growing woody grass providing structure and food in Asian forests"}),
            ("Moss", {"role": "Primary producer", "description": "Non-vascular plant retaining moisture on forest floors and rocks"}),
            ("Lichen", {"role": "Primary producer", "description": "Symbiotic algae-fungus organism colonizing bare rock and bark"}),
            ("Water Lilies", {"role": "Primary producer", "description": "Floating aquatic plants shading freshwater surfaces"}),
            ("Coral Polyps", {"role": "Primary producer", "description": "Colonial organisms secreting calcium carbonate to build reef structures"}),
            ("Sea Anemones", {"role": "Primary producer", "description": "Sessile cnidarians with photosynthetic symbiotic algae"}),
            ("Reed Grass", {"role": "Primary producer", "description": "Tall wetland grass filtering water and sheltering marsh wildlife"}),
            ("Orchids", {"role": "Primary producer", "description": "Epiphytic flowering plants adding canopy-level diversity"}),
            ("Bromeliads", {"role": "Primary producer", "description": "Rosette-forming epiphytes that collect rainwater in leaf tanks"}),
            ("Ficus Trees", {"role": "Primary producer", "description": "Keystone fig trees fruiting year-round, sustaining tropical frugivores"}),
            ("Palm Trees", {"role": "Primary producer", "description": "Tropical trees producing fruit, oil, and canopy structure"}),
        ]
        for name, meta in producer_specs:
            a = self.make_agent(
                name, rng,
                energy=2.0 + rng.uniform(0, 1.5),
                resources=3.0 + rng.uniform(0, 3),
                influence=0.2 + rng.uniform(0, 0.2),
                ideology=[rng.uniform(0, 0.3), rng.uniform(0, 0.3)],
                metadata=meta,
            )
            producers.append(a)
            all_species.append(a)
            graph.add_node(a)

        # Primary consumers / herbivores (35 species)
        herbivores = []
        herbivore_specs = [
            ("Reef Fish", {"role": "Primary consumer", "description": "Diverse coral-dwelling fish grazing on algae and small invertebrates"}),
            ("Deer", {"role": "Primary consumer", "description": "Forest-edge browser regulating understory vegetation"}),
            ("Zebra", {"role": "Primary consumer", "description": "Migratory grazer maintaining savanna grassland structure"}),
            ("Lake Trout", {"role": "Primary consumer", "description": "Cold-water fish feeding on aquatic invertebrates and plankton"}),
            ("Insects", {"role": "Primary consumer", "description": "Abundant arthropods forming the nutritional base for many predators"}),
            ("Rabbits", {"role": "Primary consumer", "description": "Prolific herbivore shaping grassland and meadow plant composition"}),
            ("Parrots", {"role": "Primary consumer", "description": "Seed-eating birds aiding tropical forest seed dispersal"}),
            ("Butterflies", {"role": "Primary consumer", "description": "Nectar-feeding insects and important plant pollinators"}),
            ("Sea Turtles", {"role": "Primary consumer", "description": "Long-lived marine reptile grazing on seagrass beds"}),
            ("Manatees", {"role": "Primary consumer", "description": "Large aquatic herbivore keeping waterways clear of vegetation"}),
            ("Hummingbirds", {"role": "Primary consumer", "description": "Nectar-specialist birds co-evolved with tropical flowers"}),
            ("Fruit Bats", {"role": "Primary consumer", "description": "Nocturnal flying mammals dispersing seeds of tropical fruits"}),
            ("Caterpillars", {"role": "Primary consumer", "description": "Larval-stage lepidopterans consuming large quantities of foliage"}),
            ("Grasshoppers", {"role": "Primary consumer", "description": "Jumping herbivorous insects capable of swarming when abundant"}),
            ("Antelope", {"role": "Primary consumer", "description": "Swift savanna grazer forming large migratory herds"}),
            ("Hippos", {"role": "Primary consumer", "description": "Semi-aquatic megaherbivore fertilizing rivers with nutrient-rich waste"}),
            ("Freshwater Shrimp", {"role": "Primary consumer", "description": "Small crustacean filtering detritus in freshwater streams"}),
            ("Snails", {"role": "Primary consumer", "description": "Slow-moving mollusc grazing on algae and decaying plant matter"}),
            ("Crabs", {"role": "Primary consumer", "description": "Decapod crustacean scavenging detritus in mangrove and intertidal zones"}),
            ("Termites", {"role": "Primary consumer", "description": "Social insects breaking down cellulose and aerating soil"}),
            ("Leaf Beetles", {"role": "Primary consumer", "description": "Foliage-feeding beetles specializing on specific host plants"}),
            ("Monarch Butterflies", {"role": "Primary consumer", "description": "Migratory butterfly dependent on milkweed for larval development"}),
            ("Tree Frogs", {"role": "Primary consumer", "description": "Arboreal amphibian feeding on insects in canopy microclimates"}),
            ("Salamanders", {"role": "Primary consumer", "description": "Moisture-dependent amphibian inhabiting forest leaf litter"}),
            ("Tadpoles", {"role": "Primary consumer", "description": "Larval-stage amphibians grazing algae in freshwater pools"}),
            ("Aphids", {"role": "Primary consumer", "description": "Sap-sucking insects reproducing rapidly on plant stems"}),
            ("Iguanas", {"role": "Primary consumer", "description": "Large herbivorous lizard basking in tropical forest canopies"}),
            ("Tortoises", {"role": "Primary consumer", "description": "Long-lived terrestrial reptile grazing on grasses and succulents"}),
            ("Sea Urchins", {"role": "Primary consumer", "description": "Spiny echinoderms grazing algae on rocky reef substrates"}),
            ("Clownfish", {"role": "Primary consumer", "description": "Small reef fish living symbiotically within sea anemones"}),
            ("Minnows", {"role": "Primary consumer", "description": "Small freshwater fish feeding on algae and micro-invertebrates"}),
            ("Sparrows", {"role": "Primary consumer", "description": "Seed-eating passerines common in grasslands and forest edges"}),
            ("Doves", {"role": "Primary consumer", "description": "Grain- and seed-eating birds inhabiting diverse habitats"}),
            ("Bees", {"role": "Primary consumer", "description": "Essential pollinators collecting nectar and pollen from flowering plants"}),
            ("Dragonflies", {"role": "Primary consumer", "description": "Agile flying insects with aquatic larvae preying on mosquitoes"}),
        ]
        for name, meta in herbivore_specs:
            a = self.make_agent(
                name, rng,
                energy=1.2 + rng.uniform(0, 1),
                resources=1.5 + rng.uniform(0, 1.5),
                influence=0.3 + rng.uniform(0, 0.2),
                ideology=[rng.uniform(0.25, 0.55), rng.uniform(0.25, 0.55)],
                metadata=meta,
            )
            herbivores.append(a)
            all_species.append(a)
            graph.add_node(a)

        # Secondary consumers / predators (20 species)
        predators = []
        predator_specs = [
            ("Sharks", {"role": "Secondary consumer", "description": "Cartilaginous fish regulating prey populations across reef and pelagic zones"}),
            ("Jaguars", {"role": "Secondary consumer", "description": "Powerful solitary cat hunting along rainforest riverbanks"}),
            ("Lions", {"role": "Secondary consumer", "description": "Social savanna predator hunting in cooperative prides"}),
            ("Eagles", {"role": "Secondary consumer", "description": "Large raptor soaring over forests and mountains to hunt small mammals"}),
            ("Wolves", {"role": "Secondary consumer", "description": "Pack-hunting canids shaping ungulate behavior and distribution"}),
            ("Crocodiles", {"role": "Secondary consumer", "description": "Ambush predator dominating tropical rivers and estuaries"}),
            ("Foxes", {"role": "Secondary consumer", "description": "Opportunistic omnivore adapting to forest, grassland, and edge habitats"}),
            ("Hawks", {"role": "Secondary consumer", "description": "Agile raptor pursuing birds and rodents in open country"}),
            ("Otters", {"role": "Secondary consumer", "description": "Aquatic mustelid feeding on fish and shellfish in rivers and coasts"}),
            ("Snakes", {"role": "Secondary consumer", "description": "Limbless reptile controlling rodent and amphibian populations"}),
            ("Dolphins", {"role": "Secondary consumer", "description": "Intelligent marine mammal hunting schooling fish cooperatively"}),
            ("Owls", {"role": "Secondary consumer", "description": "Nocturnal raptor with silent flight hunting rodents and insects"}),
            ("Herons", {"role": "Secondary consumer", "description": "Wading bird spearing fish and frogs in shallow waters"}),
            ("Kingfishers", {"role": "Secondary consumer", "description": "Diving bird catching small fish from freshwater perches"}),
            ("Monitor Lizards", {"role": "Secondary consumer", "description": "Large predatory lizard foraging on eggs, insects, and small vertebrates"}),
            ("Barracuda", {"role": "Secondary consumer", "description": "Fast reef predator ambushing smaller fish with speed bursts"}),
            ("Piranhas", {"role": "Secondary consumer", "description": "Freshwater fish feeding in groups on fish and carrion"}),
            ("Caracals", {"role": "Secondary consumer", "description": "Agile medium cat leaping to catch birds and rodents in dry habitats"}),
            ("Hyenas", {"role": "Secondary consumer", "description": "Social scavenger-predator with powerful jaws processing bone"}),
            ("Osprey", {"role": "Secondary consumer", "description": "Fish-eating raptor diving talons-first into water to catch prey"}),
        ]
        for name, meta in predator_specs:
            a = self.make_agent(
                name, rng,
                energy=2.0 + rng.uniform(0, 1.5),
                resources=1.0 + rng.uniform(0, 1),
                influence=0.5 + rng.uniform(0, 0.4),
                ideology=[rng.uniform(0.6, 0.9), rng.uniform(0.6, 0.9)],
                metadata=meta,
            )
            predators.append(a)
            all_species.append(a)
            graph.add_node(a)

        # Apex predators (5 species)
        apexes = []
        apex_specs = [
            ("Orca", {"role": "Apex predator", "description": "Highly social marine mammal hunting seals, fish, and even whales"}),
            ("Tiger", {"role": "Apex predator", "description": "Solitary big cat controlling deer and boar populations in dense forest"}),
            ("Great White Shark", {"role": "Apex predator", "description": "Ocean's premier predator patrolling temperate and tropical coasts"}),
            ("Harpy Eagle", {"role": "Apex predator", "description": "Massive forest raptor snatching monkeys and sloths from the canopy"}),
            ("Anaconda", {"role": "Apex predator", "description": "Giant constrictor ambushing large prey along South American waterways"}),
        ]
        for name, meta in apex_specs:
            a = self.make_agent(
                name, rng,
                energy=3.0 + rng.uniform(0, 1),
                resources=1.5 + rng.uniform(0, 0.5),
                influence=1.0 + rng.uniform(0, 0.5),
                ideology=[rng.uniform(0.8, 1.0), rng.uniform(0.8, 1.0)],
                metadata=meta,
            )
            apexes.append(a)
            all_species.append(a)
            graph.add_node(a)

        # Decomposers (5 species)
        decomposers = []
        decomposer_specs = [
            ("Fungi Network", {"role": "Decomposer", "description": "Vast mycorrhizal networks breaking down wood and sharing nutrients between trees"}),
            ("Bacteria Colony", {"role": "Decomposer", "description": "Microbial communities decomposing organic matter and fixing nitrogen"}),
            ("Earthworms", {"role": "Decomposer", "description": "Soil engineers aerating earth and converting leaf litter into humus"}),
            ("Dung Beetles", {"role": "Decomposer", "description": "Insects burying and recycling animal waste, returning nutrients to soil"}),
            ("Vultures", {"role": "Decomposer", "description": "Scavenging birds rapidly consuming carrion, preventing disease spread"}),
        ]
        for name, meta in decomposer_specs:
            a = self.make_agent(
                name, rng,
                energy=1.5 + rng.uniform(0, 0.5),
                resources=2.0 + rng.uniform(0, 1),
                influence=0.2,
                ideology=[rng.uniform(0.1, 0.3), rng.uniform(0.7, 0.9)],
                metadata=meta,
            )
            decomposers.append(a)
            all_species.append(a)
            graph.add_node(a)

        # --- Keystone resources ---
        resources = [
            self.make_resource("Sunlight", resources=25.0, metadata={"description": "Solar radiation driving photosynthesis and warming habitats"}),
            self.make_resource("Freshwater", resources=12.0, metadata={"description": "Freshwater systems supporting aquatic and terrestrial life"}),
            self.make_resource("Nutrients", resources=10.0, metadata={"description": "Nitrogen, phosphorus, and trace minerals cycling through the ecosystem"}),
            self.make_resource("Oxygen", resources=15.0, metadata={"description": "Atmospheric and dissolved oxygen produced by photosynthesis"}),
            self.make_resource("Soil", resources=8.0, metadata={"description": "Living substrate of minerals, organic matter, and microorganisms anchoring plant life"}),
        ]
        for r in resources:
            graph.add_node(r)

        # --- Ecosystem processes (Ideas) ---
        ideas = [
            self.make_idea("Photosynthesis", energy=4.0, stability=3.0, metadata={"thesis": "Light energy is converted into chemical energy, forming the base of all food webs"}),
            self.make_idea("Pollination", energy=3.0, stability=2.5, metadata={"thesis": "Animal and wind transfer of pollen enables plant reproduction and genetic diversity"}),
            self.make_idea("Decomposition", energy=2.5, stability=2.5, metadata={"thesis": "Breakdown of dead organic matter returns minerals to soil, enabling new growth"}),
            self.make_idea("Migration", energy=2.0, stability=1.5, metadata={"thesis": "Seasonal movement of species redistributes nutrients and connects distant ecosystems"}),
            self.make_idea("Symbiosis", energy=2.0, stability=2.0, metadata={"thesis": "Mutualistic partnerships increase resilience and resource efficiency for both partners"}),
            self.make_idea("Seed Dispersal", energy=1.5, stability=2.0, metadata={"thesis": "Animals and wind carry seeds away from parent plants, colonizing new areas and maintaining genetic flow"}),
        ]
        for idea in ideas:
            graph.add_node(idea)

        # === FOOD WEB EDGES ===

        # Producers → Herbivores
        for herb in herbivores:
            num_food = rng.integers(2, 5)
            prey = rng.choice(producers, size=min(num_food, len(producers)), replace=False)
            for p in prey:
                graph.add_edge(self.connect(p, herb, EdgeType.RESOURCE_FLOW,
                    weight=0.4 + rng.uniform(0, 0.4), transfer_rate=0.12))

        # Herbivores → Predators
        for pred in predators:
            num_prey = rng.integers(3, 7)
            prey = rng.choice(herbivores, size=min(num_prey, len(herbivores)), replace=False)
            for p in prey:
                graph.add_edge(self.connect(p, pred, EdgeType.RESOURCE_FLOW,
                    weight=0.35 + rng.uniform(0, 0.35), transfer_rate=0.1))

        # Predators → Apex
        for apex in apexes:
            num_prey = rng.integers(3, 6)
            prey = rng.choice(predators, size=min(num_prey, len(predators)), replace=False)
            for p in prey:
                graph.add_edge(self.connect(p, apex, EdgeType.RESOURCE_FLOW,
                    weight=0.3 + rng.uniform(0, 0.3), transfer_rate=0.08))

        # Decomposers recycle from all trophic levels
        for decomp in decomposers:
            sources = rng.choice(all_species, size=rng.integers(6, 12), replace=False)
            for src in sources:
                if src is decomp:
                    continue
                graph.add_edge(self.connect(src, decomp, EdgeType.RESOURCE_FLOW,
                    weight=0.2 + rng.uniform(0, 0.2), transfer_rate=0.06))

        # === HABITAT CONNECTIONS ===
        for sp in all_species:
            num_hab = rng.integers(1, 3)
            habs = rng.choice(habitats, size=num_hab, replace=False)
            for h in habs:
                graph.add_edge(self.connect(h, sp, EdgeType.RESOURCE_FLOW,
                    weight=0.3 + rng.uniform(0, 0.3), transfer_rate=0.08))

        # Resources → Habitats
        for hab in habitats:
            for res in resources:
                if rng.random() < 0.6:
                    graph.add_edge(self.connect(res, hab, EdgeType.RESOURCE_FLOW,
                        weight=0.5 + rng.uniform(0, 0.3), transfer_rate=0.1))

        # === COMPETITION (same trophic level) ===
        for group in [producers, herbivores, predators]:
            for i, s1 in enumerate(group):
                for j, s2 in enumerate(group):
                    if i >= j:
                        continue
                    if rng.random() < 0.08:
                        graph.add_edge(self.connect(s1, s2, EdgeType.CONFLICT,
                            weight=0.2 + rng.uniform(0, 0.25), transfer_rate=0.03))

        # === ECOSYSTEM PROCESSES ===
        for p in producers:
            graph.add_edge(self.connect(ideas[0], p, EdgeType.INFORMATION,
                weight=0.5, transfer_rate=0.12))

        pollinators = [h for h in herbivores if h.label in
                       ["Bees", "Butterflies", "Monarch Butterflies", "Hummingbirds", "Fruit Bats"]]
        for p in pollinators:
            graph.add_edge(self.connect(ideas[1], p, EdgeType.INFORMATION,
                weight=0.5, transfer_rate=0.1))

        for d in decomposers:
            graph.add_edge(self.connect(ideas[2], d, EdgeType.INFORMATION,
                weight=0.5, transfer_rate=0.1))

        # Symbiosis (mutualism)
        symbiotic_pairs = [
            (producers[13], herbivores[29]),   # Coral + Clownfish
            (producers[6], herbivores[18]),     # Mangrove + Crabs
            (producers[0], herbivores[16]),     # Phytoplankton + Shrimp
        ]
        for s1, s2 in symbiotic_pairs:
            graph.add_edge(self.connect(s1, s2, EdgeType.COOPERATION,
                weight=0.6, transfer_rate=0.12))
            graph.add_edge(self.connect(s2, s1, EdgeType.COOPERATION,
                weight=0.5, transfer_rate=0.1))

        return graph
