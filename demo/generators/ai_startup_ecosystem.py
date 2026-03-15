"""
AI Startup Ecosystem demo scenario.

Mode: market_dynamics
Templates: resource, diffusion, feedback

120+ nodes simulating a tech ecosystem with large companies,
startups, VCs, market segments, and competing technologies.
Demonstrates market concentration, disruption, and resource flows.
"""

from __future__ import annotations

import numpy as np

from backend.app.dynamics import DynamicsGraph, EdgeType, NodeType
from .base import DemoGenerator


class AIStartupEcosystemDemo(DemoGenerator):
    name = "ai_startup_ecosystem"
    description = (
        "Watch AI companies compete for market share. See winner-takes-all "
        "dynamics, disruption events, and market concentration form across "
        "120+ companies and institutions."
    )
    mode_name = "market_dynamics"
    steps = 250
    seed = 2025

    def build_graph(self, rng: np.random.Generator) -> DynamicsGraph:
        graph = DynamicsGraph()

        # --- Major companies as Institutions (they trigger market_concentration) ---
        majors = []
        _MAJOR_META = {
            "MegaCorp AI": {"description": "Dominant AI company with massive compute infrastructure", "mission": "Maintain market leadership across all AI segments"},
            "DeepTech Inc": {"description": "Research-first lab pushing state-of-the-art capabilities", "mission": "Achieve artificial general intelligence"},
            "Neural Systems": {"description": "Enterprise AI platform serving Fortune 500 clients", "mission": "Make AI accessible for every business workflow"},
            "AI Foundry": {"description": "Open-source model provider challenging proprietary incumbents", "mission": "Democratize AI through open weights and research"},
            "CloudMind": {"description": "Cloud hyperscaler with integrated AI services", "mission": "Bundle AI into cloud infrastructure at scale"},
            "DataVault Corp": {"description": "Data infrastructure company pivoting to AI", "mission": "Control the data layer that all AI depends on"},
        }
        major_specs = [
            ("MegaCorp AI", 12.0),
            ("DeepTech Inc", 10.0),
            ("Neural Systems", 9.0),
            ("AI Foundry", 7.0),
            ("CloudMind", 8.0),
            ("DataVault Corp", 6.0),
        ]
        for name, res in major_specs:
            node = self.make_institution(name, resources=res, metadata=_MAJOR_META.get(name))
            majors.append(node)
            graph.add_node(node)

        # --- VC firms as Institutions ---
        vcs = []
        _VC_META = {
            "Alpha Ventures": {"description": "Tier-1 VC firm leading AI mega-rounds", "mission": "Back category-defining AI companies"},
            "Beta Capital": {"description": "Growth-stage fund specializing in enterprise AI", "mission": "Scale proven AI startups to IPO"},
            "Gamma Fund": {"description": "Early-stage fund betting on frontier research", "mission": "Find the next breakthrough before anyone else"},
            "Delta Partners": {"description": "Corporate VC arm of a major tech conglomerate", "mission": "Strategic investments for ecosystem control"},
        }
        vc_names = [
            ("Alpha Ventures", 6.0),
            ("Beta Capital", 5.0),
            ("Gamma Fund", 4.0),
            ("Delta Partners", 3.5),
        ]
        for name, res in vc_names:
            node = self.make_institution(name, resources=res, metadata=_VC_META.get(name))
            vcs.append(node)
            graph.add_node(node)

        # --- Startups (80 agents with varying energy) ---
        startups = []
        startup_sectors = {
            "LLM": ["PromptWave", "TokenForge", "LangSmith", "ChatCore",
                     "InstructAI", "DialectAI", "ConvoMint", "TextPulse",
                     "PromptLab", "GenWrite"],
            "Vision": ["PixelMind", "VisionForge", "ImageSynth", "OpticalAI",
                       "FrameNet", "DeepEye", "VisualCore", "SceneGen"],
            "Robotics": ["RoboNova", "MotionAI", "ActuatorX", "BotWorks",
                         "MechMind", "DroneLogic", "AutoPilotAI", "SwarmTech"],
            "Healthcare": ["MedAI", "DiagnosticX", "BioForge", "HealthMind",
                           "GenomicAI", "PharmaNet", "CareBot", "NeuraScan"],
            "Enterprise": ["WorkflowAI", "ProcureBot", "HRMind", "SalesPulse",
                           "DataPipe", "ComplianceAI", "FinanceBot", "AuditNet"],
            "Infrastructure": ["ModelServe", "InferEngine", "VectorDB", "EmbedStore",
                               "GPUCloud", "TrainFarm", "AnnotateAI", "PipelineX"],
            "Creative": ["ArtForge", "MusicMind", "VideoSynth", "DesignAI",
                         "WriteBot", "SoundScape", "GameGen", "StoryAI"],
            "Security": ["GuardAI", "ThreatSense", "CyberMind", "IdentityNet",
                         "FraudGuard", "SecurityBot"],
        }
        all_sector_names = list(startup_sectors.keys())
        _SECTOR_ARCHETYPES = {
            "LLM": [
                {"role": "Enterprise chatbot platform", "description": "Customer service automation for Fortune 500 companies"},
                {"role": "Legal document analyzer", "description": "AI-powered contract review and compliance checking"},
                {"role": "Translation service", "description": "Real-time multilingual translation for global teams"},
                {"role": "Code generation tool", "description": "AI pair programmer that writes and reviews production code"},
                {"role": "Content writing assistant", "description": "Long-form content generation for marketing and publishing"},
                {"role": "Conversational search engine", "description": "Natural language interface replacing keyword search"},
                {"role": "Knowledge base builder", "description": "Automated extraction and organization of institutional knowledge"},
                {"role": "LLM fine-tuning platform", "description": "No-code tools for domain-specific model customization"},
            ],
            "Vision": [
                {"role": "Medical imaging analyzer", "description": "Automated radiology screening and anomaly detection"},
                {"role": "Autonomous vehicle perception", "description": "Real-time object detection for self-driving systems"},
                {"role": "Satellite imagery platform", "description": "Geospatial intelligence from commercial satellite feeds"},
                {"role": "Quality inspection system", "description": "Defect detection on manufacturing production lines"},
                {"role": "Facial recognition provider", "description": "Identity verification for banking and access control"},
                {"role": "Retail shelf analytics", "description": "Real-time inventory and planogram compliance monitoring"},
                {"role": "Video surveillance platform", "description": "Intelligent event detection across camera networks"},
                {"role": "Augmented reality engine", "description": "Visual understanding layer for AR/VR applications"},
            ],
            "Robotics": [
                {"role": "Warehouse automation", "description": "Pick-and-place robots for fulfillment centers"},
                {"role": "Surgical robotics", "description": "Precision robotic arms for minimally invasive surgery"},
                {"role": "Agricultural robot maker", "description": "Autonomous harvesting and crop monitoring machines"},
                {"role": "Construction robotics", "description": "Automated bricklaying and site inspection drones"},
                {"role": "Last-mile delivery bot", "description": "Sidewalk and aerial delivery robots for urban logistics"},
                {"role": "Industrial inspection drone", "description": "Autonomous inspection of pipelines, towers, and infrastructure"},
                {"role": "Humanoid robotics lab", "description": "General-purpose bipedal robots for diverse environments"},
                {"role": "Robot fleet orchestrator", "description": "Multi-robot coordination software for large-scale deployments"},
            ],
            "Healthcare": [
                {"role": "Drug discovery engine", "description": "AI-driven molecular simulation to accelerate clinical pipelines"},
                {"role": "Clinical trial optimizer", "description": "Patient matching and protocol design for faster trials"},
                {"role": "Remote patient monitor", "description": "Wearable-based continuous health tracking and alerts"},
                {"role": "Mental health chatbot", "description": "Conversational therapy support between clinical sessions"},
                {"role": "Pathology AI platform", "description": "Digital slide analysis for cancer grading and diagnosis"},
                {"role": "Genomics data analyzer", "description": "Variant interpretation and pharmacogenomic profiling"},
                {"role": "Hospital operations AI", "description": "Bed management, staffing, and resource optimization"},
                {"role": "Radiology co-pilot", "description": "Second-read AI assistant for diagnostic imaging"},
            ],
            "Enterprise": [
                {"role": "Procurement optimizer", "description": "AI-driven vendor selection and spend analytics"},
                {"role": "HR talent intelligence", "description": "Automated resume screening and workforce planning"},
                {"role": "Sales forecasting engine", "description": "Pipeline prediction and deal scoring for revenue teams"},
                {"role": "Contract lifecycle manager", "description": "Automated drafting, redlining, and renewal tracking"},
                {"role": "Compliance monitoring tool", "description": "Continuous regulatory surveillance across jurisdictions"},
                {"role": "IT helpdesk automation", "description": "Ticket triage and self-service resolution for employees"},
                {"role": "Business intelligence copilot", "description": "Natural language querying of enterprise data warehouses"},
                {"role": "Expense management AI", "description": "Automated receipt parsing, policy enforcement, and auditing"},
            ],
            "Infrastructure": [
                {"role": "Model serving platform", "description": "Low-latency inference infrastructure with auto-scaling"},
                {"role": "Vector database provider", "description": "Purpose-built storage for embeddings and similarity search"},
                {"role": "ML experiment tracker", "description": "Reproducibility and versioning for training runs"},
                {"role": "Data labeling platform", "description": "Human-in-the-loop annotation with active learning"},
                {"role": "GPU cloud marketplace", "description": "On-demand GPU clusters aggregated from multiple providers"},
                {"role": "Feature store builder", "description": "Centralized feature engineering and serving for ML pipelines"},
                {"role": "LLM observability tool", "description": "Monitoring, tracing, and evaluation for production LLM apps"},
                {"role": "Training data marketplace", "description": "Curated, licensed datasets for domain-specific fine-tuning"},
            ],
            "Creative": [
                {"role": "AI art generator", "description": "Text-to-image creation for designers and illustrators"},
                {"role": "Music composition AI", "description": "Original soundtrack generation for film, games, and ads"},
                {"role": "Video editing assistant", "description": "Automated cuts, effects, and scene transitions"},
                {"role": "3D asset generator", "description": "AI-powered modeling for games and virtual worlds"},
                {"role": "Copywriting co-pilot", "description": "Ad copy and social media content at scale"},
                {"role": "Voice synthesis studio", "description": "Realistic text-to-speech and voice cloning platform"},
                {"role": "Game level designer", "description": "Procedural content generation for interactive entertainment"},
                {"role": "Brand identity engine", "description": "Automated logo, palette, and style guide creation"},
            ],
            "Security": [
                {"role": "Threat intelligence platform", "description": "Real-time aggregation and scoring of cyber threat feeds"},
                {"role": "Fraud detection engine", "description": "Transaction anomaly detection for fintech and payments"},
                {"role": "Endpoint protection AI", "description": "Behavioral analysis to stop malware and ransomware"},
                {"role": "Identity access manager", "description": "Adaptive authentication and zero-trust policy enforcement"},
                {"role": "Vulnerability scanner", "description": "Automated code and infrastructure security auditing"},
                {"role": "Phishing defense system", "description": "Email and message analysis to block social engineering"},
            ],
        }
        for sector, names in startup_sectors.items():
            archetypes = _SECTOR_ARCHETYPES.get(sector, [{}])
            for i, name in enumerate(names):
                meta = archetypes[i % len(archetypes)]
                node = self.make_agent(
                    name, rng,
                    energy=1.5 + rng.uniform(0, 2.5),
                    resources=0.5 + rng.uniform(0, 2.0),
                    influence=0.2 + rng.uniform(0, 0.5),
                    ideology=[rng.uniform(0, 1), rng.uniform(0, 1)],
                    metadata=meta,
                )
                startups.append(node)
                graph.add_node(node)

        # --- Market segments (Resource nodes) ---
        markets = []
        market_specs = [
            ("Enterprise SaaS", 18.0),
            ("Consumer AI", 15.0),
            ("Developer Tools", 10.0),
            ("Healthcare Tech", 12.0),
            ("Autonomous Systems", 8.0),
            ("Creative Tools", 7.0),
            ("Cybersecurity", 9.0),
            ("AI Infrastructure", 14.0),
        ]
        _MARKET_META = {
            "Enterprise SaaS": {"description": "B2B software market worth $200B+ annually"},
            "Consumer AI": {"description": "Direct-to-consumer AI products and assistants"},
            "Developer Tools": {"description": "APIs, SDKs, and platforms for AI developers"},
            "Healthcare Tech": {"description": "FDA-regulated AI applications in medicine"},
            "Autonomous Systems": {"description": "Self-driving vehicles, drones, and industrial robots"},
            "Creative Tools": {"description": "AI-powered content creation and design tools"},
            "Cybersecurity": {"description": "AI-driven threat detection and response market"},
            "AI Infrastructure": {"description": "GPUs, model serving, training pipelines, and vector DBs"},
        }
        for name, res in market_specs:
            node = self.make_resource(name, resources=res, metadata=_MARKET_META.get(name))
            markets.append(node)
            graph.add_node(node)

        # --- Technology trends (Ideas) ---
        ideas = []
        idea_specs = [
            ("Foundation Models", 5.0, 2.0),
            ("Edge AI Inference", 3.0, 1.5),
            ("AI Safety Research", 2.5, 2.5),
            ("Open Source AI", 4.0, 1.0),
            ("AGI Race", 2.0, 0.5),
            ("Multimodal AI", 3.5, 1.5),
            ("AI Agents", 4.0, 1.0),
            ("Synthetic Data", 2.5, 1.5),
            ("Federated Learning", 2.0, 2.0),
            ("Neuromorphic Computing", 1.5, 2.0),
        ]
        _IDEA_META = {
            "Foundation Models": {"thesis": "Large pretrained models are the platform layer of AI", "counter": "Moat erodes as open-source catches up"},
            "Edge AI Inference": {"thesis": "On-device AI delivers latency and privacy advantages", "counter": "Cloud inference keeps improving faster than edge hardware"},
            "AI Safety Research": {"thesis": "Alignment research is essential before scaling further", "counter": "Safety concerns slow progress and benefit incumbents"},
            "Open Source AI": {"thesis": "Open weights accelerate innovation and reduce concentration", "counter": "Open-sourcing frontier models enables catastrophic misuse"},
            "AGI Race": {"thesis": "First-mover advantage in AGI determines global power balance", "counter": "Racing to AGI without safeguards risks existential catastrophe"},
            "Multimodal AI": {"thesis": "Combining vision, language, and audio unlocks new applications", "counter": "Multimodal complexity increases cost without proportional value"},
            "AI Agents": {"thesis": "Autonomous AI agents will automate complex knowledge work", "counter": "Agents are unreliable and hallucinate in critical workflows"},
            "Synthetic Data": {"thesis": "Generated training data solves scarcity and privacy issues", "counter": "Model collapse from training on synthetic data degrades quality"},
            "Federated Learning": {"thesis": "Train models without centralizing sensitive data", "counter": "Communication overhead and heterogeneity limit practical adoption"},
            "Neuromorphic Computing": {"thesis": "Brain-inspired chips achieve orders-of-magnitude efficiency gains", "counter": "Software ecosystem is too immature to compete with GPUs"},
        }
        for name, energy, stability in idea_specs:
            node = self.make_idea(name, energy=energy, stability=stability, metadata=_IDEA_META.get(name))
            ideas.append(node)
            graph.add_node(node)

        # --- Competition between majors ---
        for i, m1 in enumerate(majors):
            for j, m2 in enumerate(majors):
                if i >= j:
                    continue
                graph.add_edge(self.connect(m1, m2, EdgeType.CONFLICT,
                    weight=0.4 + rng.uniform(0, 0.4), transfer_rate=0.05))

        # --- Majors compete for markets ---
        for major in majors:
            targets = rng.choice(markets, size=rng.integers(3, 6), replace=False)
            for m in targets:
                graph.add_edge(self.connect(major, m, EdgeType.RESOURCE_FLOW,
                    weight=0.5 + rng.uniform(0, 0.5), transfer_rate=0.15))

        # --- Startups compete for their sector markets ---
        sector_market_map = {
            "LLM": [0, 2, 7],        # Enterprise, Developer, Infrastructure
            "Vision": [1, 5, 4],      # Consumer, Creative, Autonomous
            "Robotics": [4, 0],       # Autonomous, Enterprise
            "Healthcare": [3],        # Healthcare
            "Enterprise": [0, 2],     # Enterprise, Developer
            "Infrastructure": [7, 2], # Infrastructure, Developer
            "Creative": [5, 1],       # Creative, Consumer
            "Security": [6, 0],       # Cybersecurity, Enterprise
        }
        idx = 0
        for sector, names in startup_sectors.items():
            market_idxs = sector_market_map[sector]
            for name in names:
                for mi in market_idxs:
                    graph.add_edge(self.connect(startups[idx], markets[mi], EdgeType.RESOURCE_FLOW,
                        weight=0.2 + rng.uniform(0, 0.4), transfer_rate=0.08))
                idx += 1

        # --- VC funding flows ---
        for vc in vcs:
            funded = rng.choice(startups, size=rng.integers(8, 16), replace=False)
            for s in funded:
                graph.add_edge(self.connect(vc, s, EdgeType.RESOURCE_FLOW,
                    weight=0.5 + rng.uniform(0, 0.5), transfer_rate=0.2))

        # --- Startup competition (within same sector) ---
        idx = 0
        for sector, names in startup_sectors.items():
            sector_startups = startups[idx:idx+len(names)]
            for i, s1 in enumerate(sector_startups):
                for j, s2 in enumerate(sector_startups):
                    if i >= j:
                        continue
                    if rng.random() < 0.25:
                        graph.add_edge(self.connect(s1, s2, EdgeType.CONFLICT,
                            weight=0.2 + rng.uniform(0, 0.3), transfer_rate=0.03))
            idx += len(names)

        # --- Technology adoption ---
        for startup in startups:
            adopted = rng.choice(ideas, size=rng.integers(1, 4), replace=False)
            for idea in adopted:
                graph.add_edge(self.connect(startup, idea, EdgeType.INFORMATION,
                    weight=0.3 + rng.uniform(0, 0.4), transfer_rate=0.1))
        for major in majors:
            adopted = rng.choice(ideas, size=rng.integers(2, 5), replace=False)
            for idea in adopted:
                graph.add_edge(self.connect(major, idea, EdgeType.INFORMATION,
                    weight=0.5 + rng.uniform(0, 0.3), transfer_rate=0.12))

        # --- Partnerships/cooperation ---
        for i, s1 in enumerate(startups):
            for j, s2 in enumerate(startups):
                if i >= j:
                    continue
                if rng.random() < 0.02:
                    graph.add_edge(self.connect(s1, s2, EdgeType.COOPERATION,
                        weight=0.3 + rng.uniform(0, 0.3), transfer_rate=0.08))

        # --- Major → startup influence ---
        for major in majors:
            influenced = rng.choice(startups, size=rng.integers(8, 15), replace=False)
            for s in influenced:
                graph.add_edge(self.connect(major, s, EdgeType.INFLUENCE,
                    weight=0.3 + rng.uniform(0, 0.3), transfer_rate=0.08))

        return graph
