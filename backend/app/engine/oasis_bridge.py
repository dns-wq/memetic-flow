"""
OASIS Bridge — maps OASIS agent actions to typed graph updates.

Reads action JSONL files produced by OASIS simulation runners and
translates them into DynamicsGraph mutations (node state changes,
new edges, weight adjustments).

Mapping table:
    OASIS Action        → Graph Update
    ─────────────────────────────────────────────────────────
    CREATE_POST         → Create Idea node, add Information edges to followers
    LIKE_POST           → Increase edge weight on Information edge
    DISLIKE_POST        → Decrease edge weight on Information edge
    FOLLOW              → Create Influence edge (follower → target)
    CREATE_COMMENT      → Add Information edge between commenter and post author
    REPOST / QUOTE_POST → Amplify idea node energy, create new edges
    MUTE                → Remove Influence edge
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..dynamics.graph import DynamicsGraph
from ..dynamics.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeState,
    NodeType,
)
from .text_analyzer import FALLBACK_SIGNALS, TextAnalyzer


def _stable_id(prefix: str, *parts: str) -> str:
    """Deterministic short ID from a prefix and content parts."""
    h = hashlib.md5(":".join(parts).encode()).hexdigest()[:10]
    return f"{prefix}_{h}"


class OASISBridge:
    """Ingests OASIS action logs and applies them to a DynamicsGraph.

    When a ``TextAnalyzer`` is provided, text content of posts and
    comments is analysed so that mathematical values (influence gain,
    energy boost, edge types) are *informed by the text* rather than
    using fixed constants.  When no analyser is present the original
    fixed-constant behaviour is preserved.
    """

    def __init__(
        self,
        graph: DynamicsGraph,
        text_analyzer: TextAnalyzer | None = None,
    ) -> None:
        self._graph = graph
        self._analyzer = text_analyzer
        # Track agent name → node_id mapping
        self._agent_nodes: dict[str, str] = {}
        # Track post content hash → idea node_id mapping
        self._idea_nodes: dict[str, str] = {}

    def _idea_labels(self) -> list[str]:
        """Return labels of current Idea nodes for topic relevance context."""
        return [
            n.label for n in self._graph.nodes.values()
            if n.node_type == NodeType.IDEA
        ]

    def _ensure_agent(self, agent_name: str) -> str:
        """Get or create an Agent node for the given agent name."""
        if agent_name in self._agent_nodes:
            return self._agent_nodes[agent_name]

        node_id = _stable_id("agent", agent_name)
        if not self._graph.has_node(node_id):
            self._graph.add_node(GraphNode(
                node_id=node_id,
                node_type=NodeType.AGENT,
                label=agent_name,
                state=NodeState(influence=0.5, energy=1.0),
                metadata={"oasis_name": agent_name},
            ))
        self._agent_nodes[agent_name] = node_id
        return node_id

    def _ensure_idea(self, content: str, author_name: str) -> str:
        """Get or create an Idea node for a post/comment."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        if content_hash in self._idea_nodes:
            return self._idea_nodes[content_hash]

        node_id = _stable_id("idea", content_hash)
        if not self._graph.has_node(node_id):
            label = content[:50] + "..." if len(content) > 50 else content
            self._graph.add_node(GraphNode(
                node_id=node_id,
                node_type=NodeType.IDEA,
                label=label,
                state=NodeState(energy=1.0, stability=1.0),
                metadata={"author": author_name, "content_hash": content_hash},
            ))
        self._idea_nodes[content_hash] = node_id
        return node_id

    def _ensure_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 0.5,
    ) -> GraphEdge:
        """Get existing edge or create one."""
        existing = self._graph.get_edges_between(source_id, target_id)
        for e in existing:
            if e.edge_type == edge_type:
                return e

        edge_id = _stable_id("edge", source_id, target_id, edge_type.value)
        edge = GraphEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
        )
        self._graph.add_edge(edge)
        return edge

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _handle_create_post(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        content = args.get("content", "")
        agent_name = action.get("agent_name", "unknown")
        if not content:
            return

        # Analyze text content if analyzer available
        signals = FALLBACK_SIGNALS
        if self._analyzer:
            signals = self._analyzer.analyze(content, self._idea_labels())

        agent_id = self._ensure_agent(agent_name)
        idea_id = self._ensure_idea(content, agent_name)

        # Author → Idea (created it)
        self._ensure_edge(agent_id, idea_id, EdgeType.INFORMATION, weight=1.0)

        # Influence boost: modulated by persuasiveness
        agent = self._graph.get_node(agent_id)
        influence_delta = 0.02 + signals.persuasiveness * 0.08  # range: 0.02..0.10
        agent.state.influence = min(1.0, agent.state.influence + influence_delta)

        # Novel posts get an energy boost
        idea = self._graph.get_node(idea_id)
        if signals.novelty > 0.7:
            idea.state.energy = min(50.0, idea.state.energy + signals.novelty)

        # Create edges to related existing ideas based on topic_relevance
        for label, relevance in signals.topic_relevance.items():
            if relevance < 0.4:
                continue
            for n in self._graph.nodes.values():
                if (n.node_type == NodeType.IDEA
                        and n.label == label
                        and n.node_id != idea_id):
                    self._ensure_edge(idea_id, n.node_id,
                                      EdgeType.INFORMATION, weight=relevance * 0.5)

        # Store signals in idea metadata
        idea.metadata["sentiment"] = signals.sentiment
        idea.metadata["persuasiveness"] = signals.persuasiveness
        idea.metadata["novelty"] = signals.novelty
        if signals.topics:
            idea.metadata["topics"] = signals.topics

    def _handle_like_post(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        content = args.get("post_content", "")
        author = args.get("post_author_name", "")
        agent_name = action.get("agent_name", "unknown")
        if not content:
            return

        liker_id = self._ensure_agent(agent_name)
        idea_id = self._ensure_idea(content, author)

        # Liker → Idea (positive engagement)
        edge = self._ensure_edge(liker_id, idea_id, EdgeType.INFORMATION)
        edge.weight = min(1.0, edge.weight + 0.1)

        # Energy boost modulated by content quality (stored in metadata)
        idea = self._graph.get_node(idea_id)
        persuasiveness = idea.metadata.get("persuasiveness", 0.5)
        energy_delta = 0.5 * (0.5 + persuasiveness)  # range: 0.25..0.75
        idea.state.energy = min(50.0, idea.state.energy + energy_delta)

    def _handle_dislike_post(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        content = args.get("post_content", "")
        author = args.get("post_author_name", "")
        agent_name = action.get("agent_name", "unknown")
        if not content:
            return

        disliker_id = self._ensure_agent(agent_name)
        idea_id = self._ensure_idea(content, author)

        # Conflict weight: more persuasive posts generate stronger disagreement
        idea = self._graph.get_node(idea_id)
        persuasiveness = idea.metadata.get("persuasiveness", 0.5)
        conflict_weight = 0.2 + persuasiveness * 0.3  # range: 0.2..0.5
        self._ensure_edge(disliker_id, idea_id, EdgeType.CONFLICT, weight=conflict_weight)

        # Stability loss scaled by sentiment extremeness
        sentiment = abs(idea.metadata.get("sentiment", 0.0))
        stability_loss = 0.05 + sentiment * 0.1  # range: 0.05..0.15
        idea.state.stability = max(0.1, idea.state.stability - stability_loss)

    def _handle_follow(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        target_name = args.get("target_user_name", "")
        agent_name = action.get("agent_name", "unknown")
        if not target_name:
            return

        follower_id = self._ensure_agent(agent_name)
        target_id = self._ensure_agent(target_name)

        self._ensure_edge(follower_id, target_id, EdgeType.INFLUENCE, weight=0.5)

    def _handle_repost(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        content = args.get("original_content", "")
        orig_author = args.get("original_author_name", "")
        agent_name = action.get("agent_name", "unknown")
        if not content:
            return

        reposter_id = self._ensure_agent(agent_name)
        idea_id = self._ensure_idea(content, orig_author)

        # Reposter amplifies the idea
        edge = self._ensure_edge(reposter_id, idea_id, EdgeType.INFORMATION)
        edge.weight = min(1.0, edge.weight + 0.2)

        # Energy boost modulated by persuasiveness
        idea = self._graph.get_node(idea_id)
        persuasiveness = idea.metadata.get("persuasiveness", 0.5)
        energy_boost = 0.5 + persuasiveness * 1.0  # range: 0.5..1.5
        idea.state.energy = min(50.0, idea.state.energy + energy_boost)

        # Create influence edge if original author exists
        if orig_author:
            orig_id = self._ensure_agent(orig_author)
            self._ensure_edge(reposter_id, orig_id, EdgeType.COOPERATION, weight=0.3)

    def _handle_quote_post(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        orig_content = args.get("original_content", "")
        orig_author = args.get("original_author_name", "")
        quote_content = args.get("quote_content", "")
        agent_name = action.get("agent_name", "unknown")
        if not orig_content:
            return

        quoter_id = self._ensure_agent(agent_name)
        orig_idea_id = self._ensure_idea(orig_content, orig_author)

        # Quote creates a new idea linked to the original
        if quote_content:
            # Analyze quote text if analyzer available
            signals = FALLBACK_SIGNALS
            if self._analyzer:
                signals = self._analyzer.analyze(quote_content, self._idea_labels())

            quote_idea_id = self._ensure_idea(quote_content, agent_name)
            self._ensure_edge(quoter_id, quote_idea_id, EdgeType.INFORMATION, weight=1.0)

            # Sentiment determines edge type to original: negative → CONFLICT, positive → INFORMATION
            if signals.sentiment < -0.3:
                self._ensure_edge(quote_idea_id, orig_idea_id, EdgeType.CONFLICT,
                                  weight=0.3 + abs(signals.sentiment) * 0.4)
            else:
                self._ensure_edge(quote_idea_id, orig_idea_id, EdgeType.INFORMATION,
                                  weight=0.5 + signals.sentiment * 0.3)

            # Store signals in quote idea metadata
            quote_idea = self._graph.get_node(quote_idea_id)
            quote_idea.metadata["sentiment"] = signals.sentiment
            quote_idea.metadata["persuasiveness"] = signals.persuasiveness
            if signals.topics:
                quote_idea.metadata["topics"] = signals.topics

        # Boost original idea
        orig_idea = self._graph.get_node(orig_idea_id)
        orig_idea.state.energy = min(50.0, orig_idea.state.energy + 0.5)

    def _handle_create_comment(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        content = args.get("content", "")
        post_author = args.get("post_author_name", "")
        agent_name = action.get("agent_name", "unknown")
        if not content:
            return

        # Analyze comment text if analyzer available
        signals = FALLBACK_SIGNALS
        if self._analyzer:
            signals = self._analyzer.analyze(content, self._idea_labels())

        commenter_id = self._ensure_agent(agent_name)
        comment_idea_id = self._ensure_idea(content, agent_name)

        # Commenter → Comment idea
        self._ensure_edge(commenter_id, comment_idea_id, EdgeType.INFORMATION, weight=1.0)

        # Store signals in comment idea metadata
        comment_idea = self._graph.get_node(comment_idea_id)
        comment_idea.metadata["sentiment"] = signals.sentiment
        comment_idea.metadata["persuasiveness"] = signals.persuasiveness
        if signals.topics:
            comment_idea.metadata["topics"] = signals.topics

        # Interaction edge: negative sentiment → CONFLICT, positive → INFLUENCE
        if post_author:
            author_id = self._ensure_agent(post_author)
            if signals.sentiment < -0.3:
                self._ensure_edge(commenter_id, author_id, EdgeType.CONFLICT,
                                  weight=0.2 + abs(signals.sentiment) * 0.3)
            else:
                weight = 0.3 + signals.persuasiveness * 0.2  # range: 0.3..0.5
                self._ensure_edge(commenter_id, author_id, EdgeType.INFLUENCE, weight=weight)

    def _handle_mute(self, action: dict[str, Any]) -> None:
        args = action.get("action_args", {})
        target_name = args.get("target_user_name", "")
        agent_name = action.get("agent_name", "unknown")
        if not target_name:
            return

        muter_id = self._ensure_agent(agent_name)
        target_id = self._ensure_agent(target_name)

        # Remove influence edges between the two
        for edge in list(self._graph.edges.values()):
            if (
                edge.source_id == muter_id
                and edge.target_id == target_id
                and edge.edge_type == EdgeType.INFLUENCE
            ):
                self._graph.remove_edge(edge.edge_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    _HANDLERS = {
        "CREATE_POST": "_handle_create_post",
        "LIKE_POST": "_handle_like_post",
        "DISLIKE_POST": "_handle_dislike_post",
        "FOLLOW": "_handle_follow",
        "REPOST": "_handle_repost",
        "QUOTE_POST": "_handle_quote_post",
        "CREATE_COMMENT": "_handle_create_comment",
        "LIKE_COMMENT": "_handle_like_post",  # Same logic as like_post
        "DISLIKE_COMMENT": "_handle_dislike_post",  # Same logic
        "MUTE": "_handle_mute",
    }

    def ingest_action(self, action: dict[str, Any]) -> None:
        """Process a single OASIS action and update the graph."""
        action_type = action.get("action_type", "")
        handler_name = self._HANDLERS.get(action_type)
        if handler_name:
            getattr(self, handler_name)(action)

    def ingest_actions(self, actions: list[dict[str, Any]]) -> int:
        """Process a batch of OASIS actions. Returns count processed."""
        count = 0
        for action in actions:
            # Skip event records (round_start, round_end, etc.)
            if "event_type" in action:
                continue
            if not action.get("success", True):
                continue
            self.ingest_action(action)
            count += 1
        return count

    def ingest_jsonl(self, path: str | Path) -> int:
        """Read and process an OASIS actions.jsonl file. Returns count processed."""
        path = Path(path)
        if not path.exists():
            return 0

        actions: list[dict[str, Any]] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    actions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return self.ingest_actions(actions)
