"""
Tests for demo scenario generators.

Tests that each generator produces valid graphs with reasonable
node/edge counts and that the simulation runs without errors.
Uses short step counts for speed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from demo.generators.social_media_regulation import SocialMediaRegulationDemo
from demo.generators.ai_startup_ecosystem import AIStartupEcosystemDemo
from demo.generators.civilization_from_scratch import CivilizationFromScratchDemo
from demo.generators.ecosystem_collapse import EcosystemCollapseDemo


class _ShortRunMixin:
    """Override steps for fast testing."""
    steps = 10


class ShortSocialMedia(_ShortRunMixin, SocialMediaRegulationDemo):
    pass


class ShortAIStartup(_ShortRunMixin, AIStartupEcosystemDemo):
    pass


class ShortCivilization(_ShortRunMixin, CivilizationFromScratchDemo):
    pass


class ShortEcosystem(_ShortRunMixin, EcosystemCollapseDemo):
    pass


DEMOS = [
    ShortSocialMedia(),
    ShortAIStartup(),
    ShortCivilization(),
    ShortEcosystem(),
]

EXPECTED_MIN_NODES = {
    "social_media_regulation": 150,
    "ai_startup_ecosystem": 80,
    "civilization_from_scratch": 200,
    "ecosystem_collapse": 90,
}

EXPECTED_MIN_EDGES = {
    "social_media_regulation": 500,
    "ai_startup_ecosystem": 300,
    "civilization_from_scratch": 800,
    "ecosystem_collapse": 300,
}


class TestDemoGraphBuilding(unittest.TestCase):
    """Test that each demo builds a valid graph."""

    def test_all_demos_build_graph(self):
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                rng = np.random.default_rng(demo.seed)
                graph = demo.build_graph(rng)
                self.assertGreater(len(graph.nodes), 0)
                self.assertGreater(len(graph.edges), 0)

    def test_minimum_node_counts(self):
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                rng = np.random.default_rng(demo.seed)
                graph = demo.build_graph(rng)
                expected = EXPECTED_MIN_NODES[demo.name]
                self.assertGreaterEqual(
                    len(graph.nodes), expected,
                    f"{demo.name} has {len(graph.nodes)} nodes, expected >= {expected}",
                )

    def test_minimum_edge_counts(self):
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                rng = np.random.default_rng(demo.seed)
                graph = demo.build_graph(rng)
                expected = EXPECTED_MIN_EDGES[demo.name]
                self.assertGreaterEqual(
                    len(graph.edges), expected,
                    f"{demo.name} has {len(graph.edges)} edges, expected >= {expected}",
                )

    def test_all_edges_reference_valid_nodes(self):
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                rng = np.random.default_rng(demo.seed)
                graph = demo.build_graph(rng)
                node_ids = set(graph.nodes.keys())
                for edge in graph.edges.values():
                    self.assertIn(edge.source_id, node_ids,
                                  f"{demo.name}: edge references missing source {edge.source_id}")
                    self.assertIn(edge.target_id, node_ids,
                                  f"{demo.name}: edge references missing target {edge.target_id}")


class TestDemoGeneration(unittest.TestCase):
    """Test full generation pipeline (short runs)."""

    def test_generate_produces_files(self):
        """Each demo generates all required output files."""
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_dir = Path(tmpdir) / demo.name
                    meta = demo.generate(out_dir)

                    # Check all required files exist
                    for fname in ["metadata.json", "initial_graph.json",
                                  "metrics.json", "events.json", "snapshots.json"]:
                        fpath = out_dir / fname
                        self.assertTrue(fpath.exists(), f"Missing {fname} for {demo.name}")
                        # Verify valid JSON
                        data = json.loads(fpath.read_text())
                        self.assertIsNotNone(data)

    def test_metadata_has_required_fields(self):
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_dir = Path(tmpdir) / demo.name
                    meta = demo.generate(out_dir)

                    for field in ["name", "description", "mode", "templates",
                                  "steps", "seed", "num_nodes", "num_edges"]:
                        self.assertIn(field, meta, f"Missing {field} in {demo.name} metadata")

    def test_snapshots_have_correct_structure(self):
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_dir = Path(tmpdir) / demo.name
                    demo.generate(out_dir)

                    snaps = json.loads((out_dir / "snapshots.json").read_text())
                    self.assertGreater(len(snaps), 0)

                    snap = snaps[0]
                    self.assertIn("timestep", snap)
                    self.assertIn("nodes", snap)
                    self.assertIn("edges", snap)
                    self.assertIn("metrics", snap)

                    # Check node structure
                    node = snap["nodes"][0]
                    self.assertIn("node_id", node)
                    self.assertIn("node_type", node)
                    self.assertIn("label", node)
                    self.assertIn("state", node)

    def test_metrics_are_populated(self):
        """Metrics should have time series data after simulation."""
        for demo in DEMOS:
            with self.subTest(demo=demo.name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_dir = Path(tmpdir) / demo.name
                    demo.generate(out_dir)

                    metrics = json.loads((out_dir / "metrics.json").read_text())
                    self.assertIsInstance(metrics, dict)
                    self.assertGreater(len(metrics), 0,
                                       f"{demo.name} has no metrics")

                    # Each metric should be a list of values
                    for key, values in metrics.items():
                        self.assertIsInstance(values, list)
                        self.assertEqual(len(values), demo.steps)


class TestDemoReproducibility(unittest.TestCase):
    """Test that demos produce identical results with same seed."""

    def test_deterministic_output(self):
        demo = ShortCivilization()  # Pick one for speed
        with tempfile.TemporaryDirectory() as tmpdir:
            out1 = Path(tmpdir) / "run1"
            out2 = Path(tmpdir) / "run2"

            demo.generate(out1)
            demo.generate(out2)

            # Compare metrics
            m1 = json.loads((out1 / "metrics.json").read_text())
            m2 = json.loads((out2 / "metrics.json").read_text())
            self.assertEqual(m1, m2, "Metrics differ between runs with same seed")


if __name__ == "__main__":
    unittest.main()
