"""
Social Media Regulation demo scenario.

Mode: public_discourse
Templates: opinion, diffusion, feedback

150+ agents simulate polarization around social media regulation.
Two entrenched factions pull a moderate majority toward extremes.
Demonstrates echo chambers, coalition formation, and polarization spikes.
"""

from __future__ import annotations

import numpy as np

from backend.app.dynamics import DynamicsGraph, EdgeType, NodeType
from .base import DemoGenerator


class SocialMediaRegulationDemo(DemoGenerator):
    name = "social_media_regulation"
    description = (
        "Watch polarization form in real time as 150+ agents debate "
        "social media regulation. Coalitions crystallize around "
        "competing narratives."
    )
    mode_name = "public_discourse"
    steps = 250
    seed = 2024

    def build_graph(self, rng: np.random.Generator) -> DynamicsGraph:
        graph = DynamicsGraph()
        agents = []

        # --- Pro-regulation faction (30 agents, ideology ~0.15) ---
        pro_reg_specs = [
            {"role": "Parent activist", "goals": "Shield children from algorithmic manipulation"},
            {"role": "Public health researcher", "goals": "Document mental health impacts of social media"},
            {"role": "EU policy analyst", "goals": "Adapt GDPR-style frameworks for platform regulation"},
            {"role": "Consumer rights attorney", "goals": "Establish legal liability for algorithmic harms"},
            {"role": "Former content moderator", "goals": "Expose exploitative labor practices inside platforms"},
            {"role": "Child psychologist", "goals": "Push age-appropriate design standards for apps"},
            {"role": "Data ethicist", "goals": "Mandate transparency in automated decision-making"},
            {"role": "Disinformation researcher", "goals": "Curb the spread of coordinated inauthentic behavior"},
            {"role": "Teachers' union organizer", "goals": "Protect students from predatory ed-tech data harvesting"},
            {"role": "Civil rights campaigner", "goals": "Combat algorithmic discrimination in content delivery"},
        ]
        for i in range(30):
            spec = pro_reg_specs[i % len(pro_reg_specs)]
            a = self.make_agent(
                f"ProReg-{i+1}", rng,
                energy=1.5 + rng.uniform(0, 0.5),
                influence=0.6 + rng.uniform(0, 0.4),
                ideology=[0.05 + rng.uniform(0, 0.15), 0.4 + rng.uniform(0, 0.2)],
                metadata=spec,
            )
            agents.append(a)
            graph.add_node(a)

        # --- Anti-regulation faction (30 agents, ideology ~0.85) ---
        anti_reg_specs = [
            {"role": "Startup founder", "goals": "Prevent compliance costs from killing small competitors"},
            {"role": "First Amendment lawyer", "goals": "Defend broad speech protections against content mandates"},
            {"role": "Libertarian commentator", "goals": "Expose regulatory capture by incumbent platforms"},
            {"role": "Venture capitalist", "goals": "Preserve the investment climate for social-media startups"},
            {"role": "Open-source developer", "goals": "Keep decentralized protocols free from government licensing"},
            {"role": "Tech policy lobbyist", "goals": "Negotiate industry self-regulation as an alternative to legislation"},
            {"role": "Digital marketing strategist", "goals": "Maintain access to behavioral targeting for advertisers"},
            {"role": "Crypto-community advocate", "goals": "Prevent speech-related regulation from spilling into Web3"},
            {"role": "Small-platform operator", "goals": "Avoid one-size-fits-all rules that only Big Tech can afford"},
            {"role": "Economics professor", "goals": "Demonstrate the innovation costs of premature regulation"},
        ]
        for i in range(30):
            spec = anti_reg_specs[i % len(anti_reg_specs)]
            a = self.make_agent(
                f"AntiReg-{i+1}", rng,
                energy=1.5 + rng.uniform(0, 0.5),
                influence=0.6 + rng.uniform(0, 0.4),
                ideology=[0.85 + rng.uniform(0, 0.15), 0.4 + rng.uniform(0, 0.2)],
                metadata=spec,
            )
            agents.append(a)
            graph.add_node(a)

        # --- Moderate majority (90 agents, ideology ~0.5 but spread) ---
        undecided_specs = [
            {"role": "Local journalist", "goals": "Report fairly on both sides of the regulation debate"},
            {"role": "Small business owner", "goals": "Understand how regulation would affect ad-supported revenue"},
            {"role": "College student", "goals": "Form an evidence-based opinion on platform governance"},
            {"role": "Suburban parent", "goals": "Weigh child-safety benefits against free-expression concerns"},
            {"role": "Retired teacher", "goals": "Evaluate whether regulation improves civic discourse"},
            {"role": "Independent app developer", "goals": "Assess whether new rules help or hinder small creators"},
            {"role": "Community librarian", "goals": "Preserve open access to information while limiting harmful content"},
            {"role": "Healthcare worker", "goals": "Determine if platform changes could reduce health misinformation"},
            {"role": "Freelance graphic designer", "goals": "Figure out how content rules would reshape creative work online"},
            {"role": "Municipal council member", "goals": "Decide whether to endorse state-level social media legislation"},
        ]
        for i in range(90):
            spec = undecided_specs[i % len(undecided_specs)]
            a = self.make_agent(
                f"Citizen-{i+1}", rng,
                energy=1.0,
                influence=0.3 + rng.uniform(0, 0.3),
                ideology=[0.3 + rng.uniform(0, 0.4), 0.2 + rng.uniform(0, 0.6)],
                metadata=spec,
            )
            agents.append(a)
            graph.add_node(a)

        pro_reg = agents[:30]
        anti_reg = agents[30:60]
        moderates = agents[60:]

        # --- Influencers (high-energy agents) ---
        influencer_specs = [
            ("Senator_ProTech", {"description": "Senior senator chairing the tech committee", "role": "Legislator", "goals": "Pass bipartisan digital regulation"}),
            ("TechCEO", {"description": "CEO of the largest social media platform", "role": "Tech executive", "goals": "Preserve industry self-regulation"}),
            ("PrivacyAdvocate", {"description": "High-profile consumer privacy campaigner", "role": "Activist", "goals": "Ensure user data protection and transparency"}),
            ("MediaHost_A", {"description": "Prime-time cable news anchor with a pro-regulation stance", "role": "Media personality", "goals": "Expose platform harms to the public"}),
            ("MediaHost_B", {"description": "Popular podcast host skeptical of government overreach", "role": "Media personality", "goals": "Defend open internet and free expression"}),
            ("AcademicExpert", {"description": "Leading researcher on social media's societal effects", "role": "Academic", "goals": "Promote evidence-based policy recommendations"}),
            ("DigitalRightsLawyer", {"description": "Constitutional attorney specializing in digital speech", "role": "Legal expert", "goals": "Balance free speech with platform accountability"}),
            ("StartupFounder", {"description": "Founder of a rising decentralized social platform", "role": "Entrepreneur", "goals": "Prevent regulation that entrenches incumbents"}),
        ]
        influencers = []
        for i, (name, meta) in enumerate(influencer_specs):
            # Alternating factions
            ideo = [0.1, 0.5] if i % 2 == 0 else [0.9, 0.5]
            a = self.make_agent(
                name, rng,
                energy=3.0 + rng.uniform(0, 1),
                influence=1.5 + rng.uniform(0, 0.5),
                ideology=ideo,
                metadata=meta,
            )
            influencers.append(a)
            graph.add_node(a)

        # --- Ideas (15 competing narratives) ---
        ideas = []
        idea_specs = [
            ("Platform Safety Bill", 4.0, 2.0, {"thesis": "Platforms must be legally liable for harmful content", "counter": "Liability stifles innovation and free expression"}),
            ("Free Speech Defense", 4.0, 2.0, {"thesis": "Online speech deserves the same protections as offline speech", "counter": "Unmoderated platforms amplify disinformation and harassment"}),
            ("Algorithm Transparency", 2.5, 1.5, {"thesis": "Users deserve to know how content is ranked and promoted", "counter": "Algorithmic disclosure reveals trade secrets and aids manipulation"}),
            ("Self-Regulation Works", 2.0, 1.0, {"thesis": "Industry voluntary standards adapt faster than legislation", "counter": "Self-regulation has repeatedly failed to prevent documented harms"}),
            ("Digital Rights Framework", 2.0, 1.5, {"thesis": "A unified charter of digital rights protects users and innovators alike", "counter": "Codifying rights online creates rigid rules that lag behind technology"}),
            ("Data Privacy Act", 3.0, 2.0, {"thesis": "Strict data-collection limits protect consumers from surveillance capitalism", "counter": "Aggressive privacy rules cripple ad-funded services that keep the internet free"}),
            ("Content Moderation Is Censorship", 3.0, 1.0, {"thesis": "Removing lawful speech under vague policies silences legitimate voices", "counter": "Content moderation is necessary to prevent real-world harm from viral misinformation"}),
            ("Child Safety Online", 3.5, 2.5, {"thesis": "Platforms must implement age verification and safety-by-design for minors", "counter": "Age-gating undermines privacy and restricts young people's access to information"}),
            ("Innovation Stifling", 2.5, 1.0, {"thesis": "Heavy regulation drives startups overseas and entrenches incumbents", "counter": "Clear rules create a level playing field that actually encourages healthy competition"}),
            ("Global Competitiveness Risk", 2.0, 1.5, {"thesis": "Domestic regulation puts national tech firms at a disadvantage globally", "counter": "Leading on regulation sets international standards that benefit domestic companies long-term"}),
            ("Mental Health Crisis", 2.5, 2.0, {"thesis": "Addictive platform design is driving a youth mental-health epidemic", "counter": "Correlation is not causation; mental health trends have many contributing factors"}),
            ("Market Self-Correction", 1.5, 1.0, {"thesis": "Consumer choice and competition will naturally punish bad actors", "counter": "Network effects create monopolies that prevent meaningful consumer switching"}),
            ("Whistleblower Revelations", 2.0, 0.8, {"thesis": "Internal documents prove platforms knowingly prioritized profit over safety", "counter": "Leaked documents are taken out of context and misrepresent nuanced internal debates"}),
            ("Constitutional Rights", 2.5, 2.0, {"thesis": "First Amendment principles must guide any regulation of online speech", "counter": "The First Amendment constrains government, not private platforms making editorial choices"}),
            ("Empirical Evidence Needed", 1.5, 1.5, {"thesis": "Policy should wait for rigorous, peer-reviewed research on platform effects", "counter": "Demanding perfect evidence delays action while harms continue to accumulate"}),
        ]
        for name, energy, stability, meta in idea_specs:
            idea = self.make_idea(name, energy=energy, stability=stability, metadata=meta)
            ideas.append(idea)
            graph.add_node(idea)

        # --- Institutions ---
        insts = [
            self.make_institution("Tech Industry Association", resources=5.0, metadata={"description": "Major tech companies' lobbying arm", "mission": "Preserve industry self-regulation"}),
            self.make_institution("Consumer Protection Bureau", resources=3.0, metadata={"description": "Federal agency safeguarding consumer interests", "mission": "Enforce fair practices and protect users from platform abuses"}),
            self.make_institution("Congressional Committee", resources=4.0, metadata={"description": "Bipartisan legislative committee on technology policy", "mission": "Draft and advance social media regulation legislation"}),
            self.make_institution("Digital Rights NGO", resources=2.0, metadata={"description": "Non-profit advocacy group for online civil liberties", "mission": "Defend digital privacy, free expression, and open access"}),
            self.make_institution("Research Institute", resources=2.5, metadata={"description": "Independent research body studying technology and society", "mission": "Produce rigorous, non-partisan evidence on platform impacts"}),
        ]
        for inst in insts:
            graph.add_node(inst)

        # --- Dense intra-faction edges ---
        for faction in [pro_reg, anti_reg]:
            for i, a1 in enumerate(faction):
                for j, a2 in enumerate(faction):
                    if i >= j:
                        continue
                    if rng.random() < 0.35:
                        w = 0.5 + rng.uniform(0, 0.5)
                        graph.add_edge(self.connect(a1, a2, EdgeType.INFLUENCE, weight=w, transfer_rate=0.15))
                        graph.add_edge(self.connect(a2, a1, EdgeType.INFLUENCE, weight=w * 0.8, transfer_rate=0.12))

        # --- Sparse cross-faction edges ---
        for a1 in pro_reg:
            for a2 in anti_reg:
                if rng.random() < 0.03:
                    graph.add_edge(self.connect(a1, a2, EdgeType.INFLUENCE, weight=0.15, transfer_rate=0.04))

        # --- Moderates influenced by both factions ---
        for mod in moderates:
            # 2-4 connections to faction members
            num_inf = rng.integers(2, 5)
            sources = list(rng.choice(pro_reg + anti_reg, size=num_inf, replace=False))
            for src in sources:
                graph.add_edge(self.connect(
                    src, mod, EdgeType.INFLUENCE,
                    weight=0.3 + rng.uniform(0, 0.3),
                    transfer_rate=0.1,
                ))

        # --- Moderate-to-moderate connections ---
        for i, m1 in enumerate(moderates):
            for j, m2 in enumerate(moderates):
                if i >= j:
                    continue
                if rng.random() < 0.06:
                    graph.add_edge(self.connect(m1, m2, EdgeType.INFLUENCE, weight=0.25, transfer_rate=0.08))

        # --- Influencers broadcast to many agents ---
        for inf in influencers:
            targets = rng.choice(agents, size=25, replace=False)
            for t in targets:
                graph.add_edge(self.connect(
                    inf, t, EdgeType.INFLUENCE,
                    weight=0.6 + rng.uniform(0, 0.3),
                    transfer_rate=0.18,
                ))

        # --- Idea connections ---
        # Pro-regulation ideas connected to pro-reg agents
        pro_ideas = [ideas[0], ideas[2], ideas[5], ideas[7], ideas[10]]
        for idea in pro_ideas:
            for a in pro_reg:
                if rng.random() < 0.3:
                    graph.add_edge(self.connect(a, idea, EdgeType.INFORMATION, weight=0.6, transfer_rate=0.15))

        # Anti-regulation ideas connected to anti-reg agents
        anti_ideas = [ideas[1], ideas[3], ideas[6], ideas[8], ideas[11], ideas[13]]
        for idea in anti_ideas:
            for a in anti_reg:
                if rng.random() < 0.3:
                    graph.add_edge(self.connect(a, idea, EdgeType.INFORMATION, weight=0.6, transfer_rate=0.15))

        # Neutral ideas available to moderates
        neutral_ideas = [ideas[4], ideas[9], ideas[12], ideas[14]]
        for idea in neutral_ideas:
            for a in moderates:
                if rng.random() < 0.08:
                    graph.add_edge(self.connect(a, idea, EdgeType.INFORMATION, weight=0.3, transfer_rate=0.08))

        # --- Institution edges ---
        # Tech lobby funds anti-regulation
        for a in anti_reg:
            if rng.random() < 0.2:
                graph.add_edge(self.connect(insts[0], a, EdgeType.RESOURCE_FLOW, weight=0.5, transfer_rate=0.15))

        # Consumer bureau supports pro-regulation
        for a in pro_reg:
            if rng.random() < 0.2:
                graph.add_edge(self.connect(insts[1], a, EdgeType.RESOURCE_FLOW, weight=0.4, transfer_rate=0.1))

        # NGO pushes digital rights
        for a in moderates[:30]:
            if rng.random() < 0.15:
                graph.add_edge(self.connect(insts[3], a, EdgeType.INFORMATION, weight=0.3, transfer_rate=0.08))

        # Idea conflicts
        conflict_pairs = [(0, 1), (0, 3), (5, 6), (7, 8), (2, 11)]
        for i, j in conflict_pairs:
            graph.add_edge(self.connect(ideas[i], ideas[j], EdgeType.CONFLICT, weight=0.5, transfer_rate=0.03))
            graph.add_edge(self.connect(ideas[j], ideas[i], EdgeType.CONFLICT, weight=0.5, transfer_rate=0.03))

        return graph
