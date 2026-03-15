"""Tests for the OASIS ↔ dynamics graph bridge."""

import json
import tempfile
from pathlib import Path

import pytest

from app.dynamics import DynamicsGraph, EdgeType, NodeType
from app.engine.oasis_bridge import OASISBridge


def _action(action_type, agent_name="alice", **args):
    return {
        "round": 1,
        "timestamp": "2025-01-01T00:00:00",
        "platform": "twitter",
        "agent_id": 1,
        "agent_name": agent_name,
        "action_type": action_type,
        "action_args": args,
        "result": None,
        "success": True,
    }


class TestCreatePost:
    def test_creates_agent_and_idea_nodes(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="Hello world"))
        assert len(g.nodes) == 2
        types = {n.node_type for n in g.nodes.values()}
        assert NodeType.AGENT in types
        assert NodeType.IDEA in types

    def test_creates_information_edge(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="Hello"))
        info_edges = g.edges_by_type(EdgeType.INFORMATION)
        assert len(info_edges) == 1

    def test_boosts_agent_influence(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="post1"))
        bridge.ingest_action(_action("CREATE_POST", content="post2"))
        agent = [n for n in g.nodes.values() if n.node_type == NodeType.AGENT][0]
        assert agent.state.influence > 0.5


class TestLikePost:
    def test_boosts_idea_energy(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="Great idea"))
        bridge.ingest_action(_action(
            "LIKE_POST", agent_name="bob",
            post_content="Great idea", post_author_name="alice",
        ))
        ideas = [n for n in g.nodes.values() if n.node_type == NodeType.IDEA]
        assert ideas[0].state.energy > 1.0


class TestDislikePost:
    def test_creates_conflict_edge(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="Bad take"))
        bridge.ingest_action(_action(
            "DISLIKE_POST", agent_name="bob",
            post_content="Bad take", post_author_name="alice",
        ))
        conflict_edges = g.edges_by_type(EdgeType.CONFLICT)
        assert len(conflict_edges) == 1

    def test_reduces_stability(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="Controversial"))
        bridge.ingest_action(_action(
            "DISLIKE_POST", agent_name="bob",
            post_content="Controversial", post_author_name="alice",
        ))
        ideas = [n for n in g.nodes.values() if n.node_type == NodeType.IDEA]
        assert ideas[0].state.stability < 1.0


class TestFollow:
    def test_creates_influence_edge(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("FOLLOW", target_user_name="bob"))
        influence_edges = g.edges_by_type(EdgeType.INFLUENCE)
        assert len(influence_edges) == 1

    def test_creates_both_agent_nodes(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("FOLLOW", target_user_name="bob"))
        agents = g.nodes_by_type(NodeType.AGENT)
        assert len(agents) == 2


class TestRepost:
    def test_boosts_idea_energy(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="Original"))
        bridge.ingest_action(_action(
            "REPOST", agent_name="bob",
            original_content="Original", original_author_name="alice",
        ))
        ideas = [n for n in g.nodes.values() if n.node_type == NodeType.IDEA]
        assert ideas[0].state.energy > 1.5

    def test_creates_cooperation_edge(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action(
            "REPOST", agent_name="bob",
            original_content="Content", original_author_name="alice",
        ))
        coop_edges = g.edges_by_type(EdgeType.COOPERATION)
        assert len(coop_edges) == 1


class TestCreateComment:
    def test_creates_influence_to_author(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action(
            "CREATE_COMMENT", agent_name="bob",
            content="I agree", post_author_name="alice",
        ))
        influence_edges = g.edges_by_type(EdgeType.INFLUENCE)
        assert len(influence_edges) == 1


class TestMute:
    def test_removes_influence_edge(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("FOLLOW", target_user_name="bob"))
        assert len(g.edges_by_type(EdgeType.INFLUENCE)) == 1

        bridge.ingest_action(_action("MUTE", target_user_name="bob"))
        assert len(g.edges_by_type(EdgeType.INFLUENCE)) == 0


class TestBatchIngestion:
    def test_ingest_actions_skips_events(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        actions = [
            {"event_type": "round_start", "round": 1},
            _action("CREATE_POST", content="Hello"),
            {"event_type": "round_end", "round": 1},
        ]
        count = bridge.ingest_actions(actions)
        assert count == 1

    def test_ingest_actions_skips_failures(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        failed = _action("CREATE_POST", content="Fail")
        failed["success"] = False
        count = bridge.ingest_actions([failed])
        assert count == 0

    def test_ingest_unknown_action_type(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        count = bridge.ingest_actions([_action("DO_NOTHING")])
        assert count == 1  # Processed but no handler
        assert len(g.nodes) == 0  # Nothing created


class TestJSONLIngestion:
    def test_ingest_from_file(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)

        actions = [
            _action("CREATE_POST", content="Post 1"),
            _action("FOLLOW", agent_name="bob", target_user_name="alice"),
            _action("LIKE_POST", agent_name="bob", post_content="Post 1", post_author_name="alice"),
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for a in actions:
                f.write(json.dumps(a) + "\n")
            path = f.name

        count = bridge.ingest_jsonl(path)
        assert count == 3
        assert len(g.nodes_by_type(NodeType.AGENT)) == 2
        assert len(g.nodes_by_type(NodeType.IDEA)) == 1

        Path(path).unlink()

    def test_ingest_nonexistent_file(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        count = bridge.ingest_jsonl("/nonexistent/path.jsonl")
        assert count == 0


class TestIdempotency:
    def test_duplicate_actions_reuse_nodes(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("CREATE_POST", content="Same post"))
        bridge.ingest_action(_action("CREATE_POST", content="Same post"))
        # Should still be 2 nodes (1 agent + 1 idea), not 4
        assert len(g.nodes) == 2

    def test_duplicate_follow_reuses_edge(self):
        g = DynamicsGraph()
        bridge = OASISBridge(g)
        bridge.ingest_action(_action("FOLLOW", target_user_name="bob"))
        bridge.ingest_action(_action("FOLLOW", target_user_name="bob"))
        assert len(g.edges_by_type(EdgeType.INFLUENCE)) == 1
