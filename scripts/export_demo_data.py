#!/usr/bin/env python3
"""
Export pipeline results from the running backend to static JSON files
for the demo site. Fetches graph, snapshots (sampled), metrics, and events
for each scenario.

Usage:
    python scripts/export_demo_data.py

Requires the backend to be running at http://localhost:5001.
"""

import json
import os
import sys
import requests
from pathlib import Path

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5001")

# Define scenarios to export
SCENARIOS = [
    {
        "name": "ai_governance",
        "sim_id": "88d8a128d901",
        "title": "AI Governance Priorities 2026",
        "source": "Partnership on AI",
        "source_url": "https://partnershiponai.org",
        "description": "How major tech companies, governments, and civil society organizations shape AI governance through policy advocacy, regulatory frameworks, and public discourse.",
        "mode": "public_discourse",
        "document": "pai_ai_governance_2026.md",
    },
    {
        "name": "tech_startups",
        "sim_id": "cd55cf3b49a3",
        "title": "Tech Startup Ecosystem 2026",
        "source": "Crunchbase News",
        "source_url": "https://news.crunchbase.com",
        "description": "The dynamics of AI companies, venture capital firms, and public markets competing for capital, talent, and market dominance in the 2026 startup ecosystem.",
        "mode": "market_dynamics",
        "document": "tech_startup_trends_2026.md",
    },
    {
        "name": "chip_race",
        "sim_id": "0c42c038b4fa",
        "title": "US-China AI Chip Race",
        "source": "Compiled from Semafor, IEEE Spectrum, Time, SCMP",
        "source_url": "",
        "description": "The geopolitical and economic dynamics of US-China semiconductor competition: export controls, domestic chip development, supply chain dependencies, and AI company strategies.",
        "mode": "ecosystem",
        "document": "us_china_chip_race.md",
    },
]

# Snapshot sampling interval
SNAPSHOT_INTERVAL = 25


def fetch_json(path):
    """Fetch JSON from the backend API."""
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def export_scenario(scenario, output_dir):
    """Export all data for a single scenario."""
    name = scenario["name"]
    sim_id = scenario["sim_id"]
    out = Path(output_dir) / name
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Exporting: {scenario['title']} (sim_id={sim_id}) ---")

    # 1. Metadata
    metadata = {
        "name": scenario["name"],
        "title": scenario["title"],
        "source": scenario["source"],
        "source_url": scenario["source_url"],
        "description": scenario["description"],
        "mode": scenario["mode"],
        "document": scenario["document"],
        "sim_id": sim_id,
    }

    # 2. Status (to get total timesteps)
    status_data = fetch_json(f"/api/dynamics/status/{sim_id}")
    total_steps = status_data.get("timestep", 0)
    metadata["total_steps"] = total_steps
    metadata["status"] = status_data.get("status", "unknown")
    print(f"  Status: {metadata['status']}, steps: {total_steps}")

    # 3. Current graph (final state)
    graph_data = fetch_json(f"/api/dynamics/graph/{sim_id}")
    num_nodes = len(graph_data.get("nodes", []))
    num_edges = len(graph_data.get("edges", []))
    metadata["num_nodes"] = num_nodes
    metadata["num_edges"] = num_edges
    print(f"  Graph: {num_nodes} nodes, {num_edges} edges")

    with open(out / "graph.json", "w") as f:
        json.dump(graph_data, f, separators=(",", ":"))
    print(f"  Saved graph.json ({(out / 'graph.json').stat().st_size // 1024}KB)")

    # 4. Sampled snapshots
    snapshots = []
    timesteps = list(range(0, total_steps + 1, SNAPSHOT_INTERVAL))
    if total_steps not in timesteps:
        timesteps.append(total_steps)

    for ts in timesteps:
        try:
            snap = fetch_json(f"/api/dynamics/snapshot/{sim_id}/{ts}")
            snapshots.append({"timestep": ts, "data": snap})
        except Exception as e:
            print(f"  Warning: Failed to fetch snapshot at t={ts}: {e}")

    with open(out / "snapshots.json", "w") as f:
        json.dump(snapshots, f, separators=(",", ":"))
    print(f"  Saved snapshots.json ({len(snapshots)} snapshots, {(out / 'snapshots.json').stat().st_size // 1024}KB)")

    # 5. Metrics
    metrics_data = fetch_json(f"/api/dynamics/metrics/{sim_id}")
    with open(out / "metrics.json", "w") as f:
        json.dump(metrics_data, f, separators=(",", ":"))
    metric_names = list(metrics_data.keys()) if isinstance(metrics_data, dict) else []
    print(f"  Saved metrics.json ({len(metric_names)} metrics)")

    # 6. Events
    events_data = fetch_json(f"/api/dynamics/events/{sim_id}")
    with open(out / "events.json", "w") as f:
        json.dump(events_data, f, separators=(",", ":"))
    num_events = len(events_data) if isinstance(events_data, list) else 0
    print(f"  Saved events.json ({num_events} events)")

    # 7. Write metadata last (includes computed stats)
    with open(out / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved metadata.json")

    return metadata


def main():
    output_dir = Path(__file__).parent.parent / "demo-site" / "public" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Exporting demo data to: {output_dir}")
    print(f"Backend: {BASE_URL}")

    # Verify backend is reachable
    try:
        requests.get(f"{BASE_URL}/api/dynamics/templates", timeout=5)
    except Exception as e:
        print(f"ERROR: Cannot reach backend at {BASE_URL}: {e}")
        sys.exit(1)

    # Export each scenario
    all_metadata = []
    for scenario in SCENARIOS:
        try:
            meta = export_scenario(scenario, output_dir)
            all_metadata.append(meta)
        except Exception as e:
            print(f"  ERROR exporting {scenario['name']}: {e}")
            import traceback
            traceback.print_exc()

    # Write scenarios manifest
    manifest = {
        "scenarios": [
            {
                "name": m["name"],
                "title": m["title"],
                "source": m["source"],
                "description": m["description"],
                "mode": m["mode"],
                "num_nodes": m["num_nodes"],
                "num_edges": m["num_edges"],
                "total_steps": m["total_steps"],
            }
            for m in all_metadata
        ]
    }
    with open(output_dir / "scenarios.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nSaved scenarios.json manifest ({len(all_metadata)} scenarios)")

    # Export mode definitions
    modes_data = fetch_json("/api/dynamics/modes")
    with open(output_dir / "modes.json", "w") as f:
        json.dump(modes_data, f, indent=2)
    print(f"Saved modes.json")

    print(f"\n=== Export complete: {len(all_metadata)} scenarios ===")
    for m in all_metadata:
        print(f"  {m['name']}: {m['num_nodes']} nodes, {m['num_edges']} edges, {m['total_steps']} steps")


if __name__ == "__main__":
    main()
