#!/usr/bin/env python3
"""
Enrich demo site snapshot data to produce visually compelling dynamics.

The raw simulation exports have static edge weights, flat resources/influence,
and minimal metric variation. This script post-processes the exported JSON to:

1. Evolve edge weights based on connected node energy trajectories
2. Add/remove edges to simulate network rewiring
3. Vary influence and resources based on network dynamics
4. Recalculate metrics to reflect enriched data

Usage:
    python scripts/enrich_demo_data.py [--data-dir demo-site/public/data]
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Edge weight evolution
# ---------------------------------------------------------------------------
def evolve_edge_weights(snapshots: list[dict]) -> list[dict]:
    """
    Vary edge weights over time based on connected node energy.
    High-energy pairs strengthen; decaying pairs weaken.
    """
    if len(snapshots) < 2:
        return snapshots

    # Build initial energy map from snapshot 0
    first = snapshots[0]["data"]
    initial_energy = {}
    for n in first["nodes"]:
        initial_energy[n["node_id"]] = n["state"]["energy"]

    for snap in snapshots:
        data = snap["data"]
        node_map = {n["node_id"]: n for n in data["nodes"]}
        progress = snap["timestep"] / max(1, snapshots[-1]["timestep"])

        for edge in data["edges"]:
            src = node_map.get(edge["source_id"])
            tgt = node_map.get(edge["target_id"])
            if not src or not tgt:
                continue

            src_e = src["state"]["energy"]
            tgt_e = tgt["state"]["energy"]
            src_e0 = initial_energy.get(edge["source_id"], 1.0)
            tgt_e0 = initial_energy.get(edge["target_id"], 1.0)

            # Relative energy change of connected pair
            avg_now = (src_e + tgt_e) / 2
            avg_init = (src_e0 + tgt_e0) / 2
            if avg_init > 0:
                ratio = avg_now / avg_init
            else:
                ratio = 1.0

            # Edge weight evolves: strong pairs strengthen, weak pairs weaken
            # Introduce some variety based on edge type
            etype = edge.get("edge_type", "information")
            if etype == "influence":
                sensitivity = 0.6
            elif etype == "conflict":
                sensitivity = 0.8  # Conflict edges are more volatile
            elif etype == "cooperation":
                sensitivity = 0.4
            elif etype == "membership":
                sensitivity = 0.2  # Institutional edges are more stable
            else:
                sensitivity = 0.5

            # Smooth evolution: lerp from 1.0 toward target
            target_weight = max(0.1, min(3.0, ratio ** sensitivity))
            new_weight = 1.0 + (target_weight - 1.0) * min(1.0, progress * 1.5)

            # Add small random perturbation for visual interest
            new_weight *= 1.0 + (hash(edge["edge_id"] + str(snap["timestep"])) % 100 - 50) * 0.002

            edge["weight"] = round(max(0.1, min(3.0, new_weight)), 4)

    return snapshots


# ---------------------------------------------------------------------------
# Network rewiring (add/remove edges over time)
# ---------------------------------------------------------------------------
def rewire_network(snapshots: list[dict], add_rate: float = 0.03,
                   remove_rate: float = 0.02) -> list[dict]:
    """
    Add new edges between high-energy nodes and remove edges between low-energy nodes.
    """
    if len(snapshots) < 2:
        return snapshots

    rng = random.Random(42)
    base_edges = {e["edge_id"] for e in snapshots[0]["data"]["edges"]}
    edge_types = ["information", "influence", "cooperation"]
    added_edges = {}   # timestep -> list of new edges
    removed_edges = {}  # timestep -> set of edge_ids to remove

    for i, snap in enumerate(snapshots):
        if i == 0:
            continue  # Don't modify the initial state

        data = snap["data"]
        node_map = {n["node_id"]: n for n in data["nodes"]}
        nodes = data["nodes"]
        existing_pairs = set()
        for e in data["edges"]:
            existing_pairs.add((e["source_id"], e["target_id"]))
            existing_pairs.add((e["target_id"], e["source_id"]))

        progress = snap["timestep"] / max(1, snapshots[-1]["timestep"])

        # Add edges: high-energy nodes form new connections
        new_edges = []
        high_energy_nodes = sorted(nodes, key=lambda n: n["state"]["energy"], reverse=True)
        top_nodes = high_energy_nodes[:max(3, len(nodes) // 5)]

        for _ in range(max(1, int(len(nodes) * add_rate * progress))):
            src = rng.choice(top_nodes)
            tgt = rng.choice(nodes)
            if src["node_id"] == tgt["node_id"]:
                continue
            if (src["node_id"], tgt["node_id"]) in existing_pairs:
                continue

            eid = f"enr_{src['node_id'][:6]}_{tgt['node_id'][:6]}_{snap['timestep']}"
            new_edge = {
                "edge_id": eid,
                "source_id": src["node_id"],
                "target_id": tgt["node_id"],
                "edge_type": rng.choice(edge_types),
                "weight": round(0.3 + rng.random() * 0.4, 4),
                "transfer_rate": 0.1,
                "decay_rate": 0.01,
                "metadata": {},
            }
            new_edges.append(new_edge)
            existing_pairs.add((src["node_id"], tgt["node_id"]))
            existing_pairs.add((tgt["node_id"], src["node_id"]))

        # Remove edges: low-energy node pairs lose connections
        edges_to_remove = set()
        for e in data["edges"]:
            if e["edge_type"] == "membership":
                continue  # Don't remove structural edges
            src = node_map.get(e["source_id"])
            tgt = node_map.get(e["target_id"])
            if not src or not tgt:
                continue
            pair_energy = src["state"]["energy"] + tgt["state"]["energy"]
            if pair_energy < 0.5 and rng.random() < remove_rate * progress:
                edges_to_remove.add(e["edge_id"])

        # Apply changes
        data["edges"] = [e for e in data["edges"] if e["edge_id"] not in edges_to_remove]
        data["edges"].extend(new_edges)

        # Propagate added edges to all subsequent snapshots
        for j in range(i + 1, len(snapshots)):
            future_data = snapshots[j]["data"]
            future_pairs = {(e["source_id"], e["target_id"]) for e in future_data["edges"]}
            for ne in new_edges:
                if (ne["source_id"], ne["target_id"]) not in future_pairs:
                    # Copy with evolved weight
                    future_edge = dict(ne)
                    progress_j = snapshots[j]["timestep"] / max(1, snapshots[-1]["timestep"])
                    future_edge["weight"] = round(min(2.0, ne["weight"] * (1 + 0.5 * (progress_j - progress))), 4)
                    future_data["edges"].append(future_edge)

            # Also propagate removals
            future_data["edges"] = [
                e for e in future_data["edges"]
                if e["edge_id"] not in edges_to_remove
            ]

    return snapshots


# ---------------------------------------------------------------------------
# Resource and influence dynamics
# ---------------------------------------------------------------------------
def evolve_resources_and_influence(snapshots: list[dict]) -> list[dict]:
    """
    Make resources flow from low-energy to high-energy nodes (preferential attachment).
    Make influence grow with connectivity and energy.
    """
    if len(snapshots) < 2:
        return snapshots

    # Get initial resource totals to conserve
    first = snapshots[0]["data"]
    total_resources = sum(n["state"]["resources"] for n in first["nodes"])
    total_influence = sum(n["state"]["influence"] for n in first["nodes"])

    for snap in snapshots:
        data = snap["data"]
        nodes = data["nodes"]
        progress = snap["timestep"] / max(1, snapshots[-1]["timestep"])

        if progress == 0:
            continue

        # Count connections per node
        conn_count = defaultdict(int)
        for e in data["edges"]:
            conn_count[e["source_id"]] += 1
            conn_count[e["target_id"]] += 1

        # Compute fitness score for each node
        fitness = {}
        for n in nodes:
            energy = n["state"]["energy"]
            conns = conn_count.get(n["node_id"], 0)
            fitness[n["node_id"]] = energy * (1 + 0.3 * math.log1p(conns))

        total_fitness = sum(fitness.values()) or 1.0

        # Redistribute resources proportional to fitness
        for n in nodes:
            f = fitness[n["node_id"]]
            share = f / total_fitness
            base = n["state"]["resources"]
            # Lerp from initial value toward fitness-proportional value
            target = total_resources * share / max(1, len(nodes)) * len(nodes)
            n["state"]["resources"] = round(
                base * (1 - progress * 0.7) + target * (progress * 0.7), 4
            )

        # Redistribute influence based on energy + connectivity
        for n in nodes:
            conns = conn_count.get(n["node_id"], 0)
            energy = n["state"]["energy"]
            base = n["state"]["influence"]
            # Influence grows/shrinks with energy relative to mean
            mean_energy = sum(nn["state"]["energy"] for nn in nodes) / max(1, len(nodes))
            energy_ratio = energy / mean_energy if mean_energy > 0 else 1.0
            target = base * (0.5 + 0.5 * energy_ratio) * (1 + 0.15 * math.log1p(conns))
            n["state"]["influence"] = round(
                base * (1 - progress * 0.6) + target * (progress * 0.6), 4
            )

    return snapshots


# ---------------------------------------------------------------------------
# Metric recalculation
# ---------------------------------------------------------------------------
def recalculate_metrics(snapshots: list[dict], metrics: dict) -> dict:
    """
    Recalculate metrics from enriched snapshot data.
    """
    new_metrics = {name: [] for name in metrics}

    for snap in snapshots:
        data = snap["data"]
        nodes = data["nodes"]
        edges = data["edges"]
        ts = snap["timestep"]

        # num_nodes / num_edges
        new_metrics["num_nodes"].append([ts, len(nodes)])
        new_metrics["num_edges"].append([ts, len(edges)])

        # total_energy
        total_e = sum(n["state"]["energy"] for n in nodes)
        new_metrics["total_energy"].append([ts, round(total_e, 4)])

        # resource_gini
        resources = sorted([n["state"]["resources"] for n in nodes])
        n = len(resources)
        if n > 0 and sum(resources) > 0:
            cumsum = 0
            for i, r in enumerate(resources):
                cumsum += (2 * (i + 1) - n - 1) * r
            gini = cumsum / (n * sum(resources))
        else:
            gini = 0
        new_metrics["resource_gini"].append([ts, round(max(0, gini), 4)])

        # polarization_index (from ideological positions)
        positions = []
        for n in nodes:
            pos = n["state"].get("ideological_position", [])
            if pos:
                positions.append(pos)
        if len(positions) >= 2:
            # Compute pairwise ideological distance variance
            dists = []
            for i in range(min(50, len(positions))):
                for j in range(i + 1, min(50, len(positions))):
                    d = sum((a - b) ** 2 for a, b in zip(positions[i], positions[j])) ** 0.5
                    dists.append(d)
            if dists:
                mean_d = sum(dists) / len(dists)
                var_d = sum((d - mean_d) ** 2 for d in dists) / len(dists)
                polarization = min(1.0, var_d / max(0.01, mean_d))
            else:
                polarization = 0
        else:
            polarization = 0
        new_metrics["polarization_index"].append([ts, round(polarization, 4)])

        # clustering_coefficient (ratio of triangles)
        adj = defaultdict(set)
        for e in edges:
            adj[e["source_id"]].add(e["target_id"])
            adj[e["target_id"]].add(e["source_id"])
        cc_sum = 0
        cc_count = 0
        for nid, neighbors in adj.items():
            k = len(neighbors)
            if k < 2:
                continue
            triangles = 0
            nb_list = list(neighbors)
            for i in range(len(nb_list)):
                for j in range(i + 1, len(nb_list)):
                    if nb_list[j] in adj[nb_list[i]]:
                        triangles += 1
            cc_sum += 2 * triangles / (k * (k - 1))
            cc_count += 1
        clustering = cc_sum / cc_count if cc_count > 0 else 0
        new_metrics["clustering_coefficient"].append([ts, round(clustering, 4)])

        # idea_entropy (energy distribution entropy across all nodes)
        # If no idea nodes, use all nodes' energy distribution
        energies_for_entropy = [n["state"]["energy"] for n in nodes
                                if n["node_type"] == "idea"]
        if not energies_for_entropy:
            energies_for_entropy = [n["state"]["energy"] for n in nodes]
        if energies_for_entropy:
            total = sum(energies_for_entropy)
            if total > 0:
                probs = [e / total for e in energies_for_entropy]
                entropy = -sum(p * math.log(max(1e-10, p)) for p in probs)
                max_ent = math.log(max(1, len(energies_for_entropy)))
                entropy = entropy / max_ent if max_ent > 0 else 0
            else:
                entropy = 0
        else:
            entropy = 0
        new_metrics["idea_entropy"].append([ts, round(entropy, 4)])

        # institutional_cohesion
        inst_members = defaultdict(list)
        for n in nodes:
            if n.get("institution_id"):
                inst_members[n["institution_id"]].append(n)
        if inst_members:
            cohesions = []
            for iid, members in inst_members.items():
                if len(members) < 2:
                    continue
                # Cohesion = avg internal edge weight / member count
                member_ids = {m["node_id"] for m in members}
                internal_weight = 0
                for e in edges:
                    if e["source_id"] in member_ids and e["target_id"] in member_ids:
                        internal_weight += e["weight"]
                cohesions.append(internal_weight / len(members))
            cohesion = sum(cohesions) / len(cohesions) if cohesions else 0
        else:
            cohesion = 0
        new_metrics["institutional_cohesion"].append([ts, round(cohesion, 4)])

        # feedback_loop_strength (avg edge weight in cycles, approximated)
        weights = [e["weight"] for e in edges]
        if weights:
            # Use weight variance as proxy for feedback dynamics
            mean_w = sum(weights) / len(weights)
            var_w = sum((w - mean_w) ** 2 for w in weights) / len(weights)
            fb_strength = round(mean_w + var_w * 2, 4)
        else:
            fb_strength = 0
        new_metrics["feedback_loop_strength"].append([ts, fb_strength])

        # cascade_count (nodes that gained energy relative to start)
        cascade = 0
        for n in nodes:
            if n["state"]["energy"] > 1.5:
                cascade += 1
        new_metrics["cascade_count"].append([ts, cascade])

    # Now interpolate metrics to all original timestep points (not just snapshot timesteps)
    original_timesteps = set()
    for name, series in metrics.items():
        for point in series:
            original_timesteps.add(point[0])

    final_metrics = {}
    for name, new_series in new_metrics.items():
        if len(new_series) < 2:
            final_metrics[name] = new_series
            continue

        # Interpolate to all original timesteps
        interpolated = []
        for ts in sorted(original_timesteps):
            # Find bracketing snapshots
            lower = None
            upper = None
            for pt in new_series:
                if pt[0] <= ts:
                    lower = pt
                if pt[0] >= ts and upper is None:
                    upper = pt

            if lower is None:
                lower = new_series[0]
            if upper is None:
                upper = new_series[-1]

            if lower[0] == upper[0]:
                val = lower[1]
            else:
                # Linear interpolation
                t = (ts - lower[0]) / (upper[0] - lower[0])
                val = lower[1] + t * (upper[1] - lower[1])

            interpolated.append([ts, round(val, 4)])

        final_metrics[name] = interpolated

    return final_metrics


# ---------------------------------------------------------------------------
# Update final graph.json to match last snapshot
# ---------------------------------------------------------------------------
def update_final_graph(graph: dict, last_snapshot: dict) -> dict:
    """
    Update the final graph state to match the enriched last snapshot.
    """
    return last_snapshot["data"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def enrich_scenario(scenario_dir: Path) -> None:
    print(f"\n  Processing {scenario_dir.name}...")

    snapshots_path = scenario_dir / "snapshots.json"
    metrics_path = scenario_dir / "metrics.json"
    graph_path = scenario_dir / "graph.json"

    if not snapshots_path.exists():
        print(f"    Skipping: no snapshots.json")
        return

    snapshots = load_json(snapshots_path)
    metrics = load_json(metrics_path) if metrics_path.exists() else {}
    graph = load_json(graph_path) if graph_path.exists() else {}

    print(f"    Loaded {len(snapshots)} snapshots, {len(metrics)} metric series")

    # Count original edges/nodes
    if snapshots:
        n0 = len(snapshots[0]["data"]["nodes"])
        e0 = len(snapshots[0]["data"]["edges"])

    # Step 1: Evolve edge weights
    snapshots = evolve_edge_weights(snapshots)

    # Step 2: Network rewiring
    snapshots = rewire_network(snapshots, add_rate=0.04, remove_rate=0.025)

    # Step 3: Resource and influence dynamics
    snapshots = evolve_resources_and_influence(snapshots)

    if snapshots:
        n_last = len(snapshots[-1]["data"]["nodes"])
        e_last = len(snapshots[-1]["data"]["edges"])
        print(f"    Nodes: {n0} (start) -> {n_last} (end)")
        print(f"    Edges: {e0} (start) -> {e_last} (end)")

        # Check edge weight variation
        weights = [e["weight"] for e in snapshots[-1]["data"]["edges"]]
        print(f"    Edge weights: min={min(weights):.3f}, max={max(weights):.3f}, mean={sum(weights)/len(weights):.3f}")

    # Step 4: Recalculate metrics
    new_metrics = recalculate_metrics(snapshots, metrics)

    # Print metric ranges
    for name, series in new_metrics.items():
        values = [p[1] for p in series]
        mn, mx = min(values), max(values)
        rng = mx - mn
        status = "FLAT" if rng < 0.01 else f"range={rng:.4f}"
        print(f"    {name:30s}: {status}")

    # Step 5: Update final graph
    if snapshots:
        graph = update_final_graph(graph, snapshots[-1])

    # Save
    save_json(snapshots_path, snapshots)
    save_json(metrics_path, new_metrics)
    save_json(graph_path, graph)
    print(f"    Saved enriched data")


def main():
    parser = argparse.ArgumentParser(description="Enrich demo site snapshot data")
    parser.add_argument("--data-dir", default="demo-site/public/data",
                        help="Path to demo data directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist")
        return

    print("Enriching demo data for visual dynamics...")

    # Find all scenario directories
    scenarios_path = data_dir / "scenarios.json"
    if scenarios_path.exists():
        manifest = load_json(scenarios_path)
        scenario_names = [s["name"] for s in manifest.get("scenarios", [])]
    else:
        scenario_names = [d.name for d in data_dir.iterdir()
                         if d.is_dir() and (d / "snapshots.json").exists()]

    for name in scenario_names:
        scenario_dir = data_dir / name
        if scenario_dir.exists():
            enrich_scenario(scenario_dir)

    print("\nDone! Demo data enriched with dynamic edge weights, network rewiring,")
    print("resource redistribution, and recalculated metrics.")


if __name__ == "__main__":
    main()
