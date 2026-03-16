"""
Electoral dynamics — candidate positioning and probabilistic voting.

Candidates (agents with ``custom["is_candidate"]=1``) position in
ideological space.  Voters are attracted by proximity, identity
alignment, and momentum.  Elections occur periodically.

Priors from spatial voting theory (Hotelling 1929, Downs 1957).
"""

from __future__ import annotations

import math

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec


class ElectoralTemplate(DynamicsTemplate):
    name = "electoral"
    description = "Candidate positioning with proximity and strategic voting"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "strategic_voting_rate": ParameterSpec(
            0.1, 0.0, 1.0,
            "Fraction of voters who vote strategically (not sincerely)",
        ),
        "identity_weight": ParameterSpec(
            0.3, 0.0, 1.0,
            "Weight of institutional/group identity in voting decisions",
        ),
        "election_interval": ParameterSpec(
            50.0, 10.0, 500.0,
            "Steps between elections",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        strategic_rate = p["strategic_voting_rate"]
        id_weight = p["identity_weight"]
        interval = int(p["election_interval"])

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        if not agents:
            return

        candidates = [a for a in agents if a.state.custom.get("is_candidate", 0.0) >= 1.0]
        voters = [a for a in agents if a.state.custom.get("is_candidate", 0.0) < 1.0]

        # If no candidates, designate high-influence agents
        if not candidates and len(agents) >= 3:
            sorted_agents = sorted(agents, key=lambda a: a.state.influence, reverse=True)
            n_candidates = max(2, len(agents) // 10)
            for a in sorted_agents[:n_candidates]:
                a.state.custom["is_candidate"] = 1.0
            candidates = sorted_agents[:n_candidates]
            voters = [a for a in agents if a.state.custom.get("is_candidate", 0.0) < 1.0]

        if not candidates or not voters:
            return

        # --- Phase 1: Candidate positioning (drift toward voter median) ---
        for cand in candidates:
            if not cand.state.ideological_position:
                continue
            ndim = len(cand.state.ideological_position)
            # Move slightly toward voter median to attract more votes
            voter_positions = [
                v.state.ideological_position for v in voters
                if v.state.ideological_position and len(v.state.ideological_position) >= ndim
            ]
            if not voter_positions:
                continue
            median = [
                float(np.median([vp[d] for vp in voter_positions]))
                for d in range(ndim)
            ]
            for d in range(ndim):
                cand.state.ideological_position[d] += 0.02 * (
                    median[d] - cand.state.ideological_position[d]
                )

        # --- Phase 2: Election (if interval reached) ---
        if graph.timestep > 0 and graph.timestep % interval == 0:
            votes: dict[str, int] = {c.node_id: 0 for c in candidates}

            for voter in voters:
                if not voter.state.ideological_position:
                    # Random vote
                    chosen = rng.choice([c.node_id for c in candidates])
                    votes[chosen] += 1
                    continue

                ndim_v = len(voter.state.ideological_position)
                # Proximity-based utility
                utilities: dict[str, float] = {}
                for cand in candidates:
                    if not cand.state.ideological_position:
                        continue
                    ndim_c = min(ndim_v, len(cand.state.ideological_position))
                    dist = math.sqrt(sum(
                        (voter.state.ideological_position[d] - cand.state.ideological_position[d]) ** 2
                        for d in range(ndim_c)
                    ))
                    proximity = 1.0 / (1.0 + dist)

                    # Identity bonus (same institution)
                    identity_bonus = 0.0
                    if voter.institution_id and voter.institution_id == cand.institution_id:
                        identity_bonus = id_weight

                    # Momentum (current energy/influence)
                    momentum = cand.state.energy * 0.1

                    utilities[cand.node_id] = proximity + identity_bonus + momentum

                if not utilities:
                    continue

                # Strategic voting
                if rng.random() < strategic_rate:
                    # Vote for most viable non-worst candidate
                    worst = min(utilities, key=lambda k: utilities[k])
                    viable = {k: v for k, v in utilities.items() if k != worst}
                    if viable:
                        chosen = max(viable, key=lambda k: viable[k])
                    else:
                        chosen = max(utilities, key=lambda k: utilities[k])
                else:
                    # Sincere: vote for highest utility
                    chosen = max(utilities, key=lambda k: utilities[k])

                votes[chosen] += 1

            # Apply election results
            if votes:
                winner_id = max(votes, key=lambda k: votes[k])
                for cand in candidates:
                    vote_share = votes.get(cand.node_id, 0) / max(1, len(voters))
                    cand.state.custom["vote_share"] = vote_share
                    if cand.node_id == winner_id:
                        cand.state.influence = min(5.0, cand.state.influence + 0.5)
                        cand.state.energy += 1.0
                    else:
                        cand.state.energy = max(0.1, cand.state.energy - 0.2)
