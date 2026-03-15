#!/usr/bin/env python3
"""
Generate all demo scenario data for Memetic Flow.

Run from the project root:
    python -m demo.generate_all

Outputs JSON bundles to demo/data/<scenario_name>/
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from demo.generators.social_media_regulation import SocialMediaRegulationDemo
from demo.generators.ai_startup_ecosystem import AIStartupEcosystemDemo
from demo.generators.civilization_from_scratch import CivilizationFromScratchDemo
from demo.generators.ecosystem_collapse import EcosystemCollapseDemo

DEMOS = [
    SocialMediaRegulationDemo(),
    AIStartupEcosystemDemo(),
    CivilizationFromScratchDemo(),
    EcosystemCollapseDemo(),
]

DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> None:
    print(f"Generating {len(DEMOS)} demo scenarios...")
    print(f"Output directory: {DATA_DIR}\n")

    total_start = time.time()

    for demo in DEMOS:
        output_dir = DATA_DIR / demo.name
        start = time.time()
        try:
            demo.generate(output_dir)
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.1f}s\n")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  FAILED after {elapsed:.1f}s: {e}\n")
            raise

    total_elapsed = time.time() - total_start
    print(f"All demos generated in {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
