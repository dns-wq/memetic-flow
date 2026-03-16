"""
Peer review and validation — quality gate for ideas.

New ideas enter "under review" status.  Reviewer agents evaluate with
configurable accuracy.  Accepted ideas gain energy; rejected ideas
decay.  Replication periodically re-tests accepted ideas.

Priors from meta-science (Ioannidis, replication crisis studies).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import NodeType
from .base import DynamicsTemplate, ParameterSpec

# Review states
_UNDER_REVIEW, _ACCEPTED, _REJECTED, _RETRACTED = 0.0, 1.0, 2.0, 3.0


class PeerReviewTemplate(DynamicsTemplate):
    name = "peer_review"
    description = "Validation gate for ideas with reviewer accuracy and replication"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "reviewer_accuracy": ParameterSpec(
            0.8, 0.5, 1.0,
            "Probability that a reviewer correctly evaluates an idea",
        ),
        "replication_rate": ParameterSpec(
            0.02, 0.0, 0.2,
            "Probability per step that an accepted idea is retested",
        ),
        "retraction_threshold": ParameterSpec(
            0.3, 0.0, 1.0,
            "Evidence threshold below which retested ideas are retracted",
        ),
        "novelty_bias": ParameterSpec(
            0.1, -0.5, 0.5,
            "Bias toward (positive) or against (negative) novel ideas",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        accuracy = p["reviewer_accuracy"]
        replication = p["replication_rate"]
        retract_thresh = p["retraction_threshold"]
        novelty_bias = p["novelty_bias"]

        ideas = list(graph.nodes_by_type(NodeType.IDEA))
        if not ideas:
            return

        # --- Bootstrap review state ---
        for idea in ideas:
            if "review_status" not in idea.state.custom:
                # Existing ideas start as accepted; truly new ones start under review
                if idea.state.custom.get("citation_count", -1.0) >= 0.0:
                    idea.state.custom["review_status"] = _UNDER_REVIEW
                else:
                    idea.state.custom["review_status"] = _ACCEPTED

        # --- Phase 1: Review under-review ideas ---
        for idea in ideas:
            if idea.state.custom.get("review_status") != _UNDER_REVIEW:
                continue

            evidence = idea.state.custom.get("evidence_strength", 0.5)
            novelty = idea.state.custom.get("novelty", 0.5)

            # True quality = evidence strength
            # Reviewer perceives: quality + noise + novelty bias
            perceived = evidence + rng.normal(0, 0.1) + novelty * novelty_bias

            # Decision
            if perceived > 0.5:
                # Should accept; correct with probability = accuracy
                if rng.random() < accuracy:
                    idea.state.custom["review_status"] = _ACCEPTED
                    idea.state.energy = max(idea.state.energy, 2.0)
                else:
                    # False negative
                    idea.state.custom["review_status"] = _REJECTED
                    idea.state.energy *= 0.5
            else:
                # Should reject
                if rng.random() < accuracy:
                    idea.state.custom["review_status"] = _REJECTED
                    idea.state.energy *= 0.3
                else:
                    # False positive
                    idea.state.custom["review_status"] = _ACCEPTED
                    idea.state.energy = max(idea.state.energy, 1.5)

        # --- Phase 2: Replication of accepted ideas ---
        for idea in ideas:
            if idea.state.custom.get("review_status") != _ACCEPTED:
                continue
            if rng.random() > replication:
                continue

            evidence = idea.state.custom.get("evidence_strength", 0.5)
            # Replication: re-evaluate with noise
            replicated_result = evidence + rng.normal(0, 0.15)

            if replicated_result < retract_thresh:
                # Retraction!
                idea.state.custom["review_status"] = _RETRACTED
                idea.state.energy = max(0.01, idea.state.energy * 0.1)
                idea.state.stability *= 0.5

        # --- Phase 3: Status effects ---
        for idea in ideas:
            status = idea.state.custom.get("review_status", _ACCEPTED)
            if status == _ACCEPTED:
                # Accepted ideas slowly gain energy
                idea.state.energy = min(10.0, idea.state.energy + 0.01)
            elif status == _REJECTED:
                # Rejected ideas decay
                idea.state.energy = max(0.0, idea.state.energy * 0.98)
            elif status == _RETRACTED:
                # Retracted ideas heavily penalized
                idea.state.energy = max(0.0, idea.state.energy * 0.95)
                idea.state.influence = max(0.0, idea.state.influence * 0.95)
