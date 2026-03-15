"""
REST API endpoints for the dynamical simulation engine.

Provides routes for graph initialization, simulation control,
template configuration, metric retrieval, event queries,
data export, scenario comparison, and pre-run demo loading.
"""

from __future__ import annotations

import csv
import io
import json as _json_mod
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from flask import jsonify, request, Response

from . import dynamics_bp
from ..dynamics import DynamicsGraph, DynamicsStore, GraphSnapshot
from ..engine import TEMPLATE_REGISTRY, SimulationEngine
from ..metrics import MetricsCollector, PhaseTransitionDetector
from ..modes import MODE_REGISTRY
from ..services.dynamics_initializer import DynamicsInitializer

# Path to pre-generated demo data
_DEMO_DATA_DIR = Path(__file__).resolve().parents[3] / "demo" / "data"

# ---------------------------------------------------------------------------
# In-memory simulation registry
# ---------------------------------------------------------------------------

_simulations: dict[str, dict[str, Any]] = {}
_store = DynamicsStore()
_initializer = DynamicsInitializer()


def _get_sim(sim_id: str) -> dict[str, Any] | None:
    return _simulations.get(sim_id)


# ---------------------------------------------------------------------------
# Graph initialization
# ---------------------------------------------------------------------------


@dynamics_bp.route("/initialize", methods=["POST"])
def initialize():
    """Create a dynamics graph from Zep graph data.

    Expects JSON body with:
        graph_data: dict — output of GraphBuilderService.get_graph_data()
        ontology:   dict — optional ontology definition
    """
    data = request.get_json(force=True)
    graph_data = data.get("graph_data")
    if not graph_data:
        return jsonify({"error": "graph_data is required"}), 400

    ontology = data.get("ontology")
    graph = _initializer.initialize(graph_data, ontology)
    suggested = _initializer.suggest_templates(graph)

    sim_id = uuid.uuid4().hex[:12]
    snapshot = graph.snapshot()
    _store.save_snapshot(sim_id, snapshot)

    _simulations[sim_id] = {
        "graph": graph,
        "engine": None,
        "status": "initialized",
        "templates": [],
        "params": {},
        "detector": PhaseTransitionDetector(),
        "events": [],
    }

    return jsonify({
        "sim_id": sim_id,
        "num_nodes": len(snapshot.nodes),
        "num_edges": len(snapshot.edges),
        "suggested_templates": suggested,
    }), 201


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


@dynamics_bp.route("/graph/<sim_id>", methods=["GET"])
def get_graph(sim_id: str):
    """Return current graph state."""
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    snapshot = sim["graph"].snapshot()
    return jsonify(_snapshot_to_dict(snapshot))


@dynamics_bp.route("/snapshot/<sim_id>/<int:timestep>", methods=["GET"])
def get_snapshot(sim_id: str, timestep: int):
    """Return graph snapshot at a specific timestep."""
    snapshot = _store.load_snapshot(sim_id, timestep)
    if not snapshot:
        return jsonify({"error": "snapshot not found"}), 404
    return jsonify(_snapshot_to_dict(snapshot))


# ---------------------------------------------------------------------------
# Template configuration
# ---------------------------------------------------------------------------


@dynamics_bp.route("/templates", methods=["GET"])
def list_templates():
    """List all available dynamical templates."""
    templates = []
    for name, cls in TEMPLATE_REGISTRY.items():
        t = cls()
        templates.append({
            "name": t.name,
            "description": t.description,
            "required_node_types": [nt.value for nt in t.required_node_types],
            "required_edge_types": [et.value for et in t.required_edge_types],
            "parameters": {
                pname: {
                    "default": spec.default,
                    "min": spec.min_val,
                    "max": spec.max_val,
                    "description": spec.description,
                }
                for pname, spec in t.parameters.items()
            },
        })
    return jsonify(templates)


@dynamics_bp.route("/parameters/<template_name>", methods=["GET"])
def get_parameters(template_name: str):
    """Get parameter specs and priors for a template."""
    cls = TEMPLATE_REGISTRY.get(template_name)
    if not cls:
        return jsonify({"error": f"template '{template_name}' not found"}), 404

    t = cls()
    return jsonify({
        "name": t.name,
        "parameters": {
            pname: {
                "default": spec.default,
                "min": spec.min_val,
                "max": spec.max_val,
                "description": spec.description,
            }
            for pname, spec in t.parameters.items()
        },
        "priors": t.get_empirical_priors(),
    })


# ---------------------------------------------------------------------------
# Simulation modes
# ---------------------------------------------------------------------------


@dynamics_bp.route("/modes", methods=["GET"])
def list_modes():
    """List all available simulation modes."""
    modes = []
    for name, cls in MODE_REGISTRY.items():
        modes.append(cls().to_dict())
    return jsonify(modes)


@dynamics_bp.route("/modes/<mode_name>/apply", methods=["POST"])
def apply_mode(mode_name: str):
    """Apply a simulation mode to an existing simulation.

    Configures templates, parameters, and runs mode-specific graph init.

    Expects JSON body with:
        sim_id: str
        seed:   int (optional, default 42)
    """
    cls = MODE_REGISTRY.get(mode_name)
    if not cls:
        return jsonify({"error": f"mode '{mode_name}' not found"}), 404

    data = request.get_json(force=True)
    sim_id = data.get("sim_id")
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    mode = cls()
    seed = data.get("seed", 42)

    # Apply mode-specific graph initialization
    mode.initialize_graph(sim["graph"])

    # Configure engine with mode's templates and params
    template_names = mode.get_templates()
    params = mode.get_params()

    templates = []
    for tname in template_names:
        tcls = TEMPLATE_REGISTRY.get(tname)
        if tcls:
            templates.append(tcls())

    engine = SimulationEngine(
        graph=sim["graph"],
        templates=templates,
        params=params,
        seed=seed,
    )
    sim["engine"] = engine
    sim["templates"] = template_names
    sim["params"] = params
    sim["mode"] = mode
    sim["status"] = "configured"

    return jsonify({
        "status": "configured",
        "mode": mode_name,
        "templates": template_names,
        "params": params,
    })


# ---------------------------------------------------------------------------
# Template & parameter configuration
# ---------------------------------------------------------------------------


@dynamics_bp.route("/configure", methods=["POST"])
def configure():
    """Set templates and parameters for a simulation.

    Expects JSON body with:
        sim_id:    str
        templates: list[str] — template names to activate
        params:    dict[str, dict] — per-template parameter overrides (optional)
        seed:      int — random seed (optional, default 42)
    """
    data = request.get_json(force=True)
    sim_id = data.get("sim_id")
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    template_names = data.get("templates", [])
    params = data.get("params", {})
    seed = data.get("seed", 42)

    # Validate template names
    templates = []
    for name in template_names:
        cls = TEMPLATE_REGISTRY.get(name)
        if not cls:
            return jsonify({"error": f"unknown template: {name}"}), 400
        templates.append(cls())

    # Build engine
    engine = SimulationEngine(
        graph=sim["graph"],
        templates=templates,
        params=params,
        seed=seed,
    )
    sim["engine"] = engine
    sim["templates"] = template_names
    sim["params"] = params
    sim["status"] = "configured"

    return jsonify({"status": "configured", "templates": template_names})


# ---------------------------------------------------------------------------
# Simulation control
# ---------------------------------------------------------------------------


@dynamics_bp.route("/start", methods=["POST"])
def start():
    """Start the dynamics simulation.

    Expects JSON body with:
        sim_id: str
        steps:  int — number of steps to run
    """
    data = request.get_json(force=True)
    sim_id = data.get("sim_id")
    steps = data.get("steps", 100)
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404
    if not sim.get("engine"):
        return jsonify({"error": "simulation not configured — call /configure first"}), 400
    if sim["status"] == "running":
        return jsonify({"error": "simulation already running"}), 409

    sim["status"] = "running"
    engine: SimulationEngine = sim["engine"]
    detector: PhaseTransitionDetector = sim["detector"]
    collector = MetricsCollector()
    engine._metrics_collector = collector

    mode = sim.get("mode")

    def _run():
        try:
            for _ in range(steps):
                if sim["status"] != "running":
                    break
                snapshot = engine.step()
                _store.save_snapshot(sim_id, snapshot)
                # Detect phase transitions
                events = detector.update(snapshot.metrics, snapshot.timestep)
                sim["events"].extend(events)
                # Mode-specific post-step hook
                if mode:
                    mode_events = mode.post_step_hook(
                        sim["graph"], snapshot.timestep
                    )
                    sim["events"].extend(mode_events)
            sim["status"] = "completed"
        except Exception as e:
            sim["status"] = "error"
            sim["error"] = str(e)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"status": "running", "steps": steps})


@dynamics_bp.route("/stop", methods=["POST"])
def stop():
    """Stop a running simulation."""
    data = request.get_json(force=True)
    sim_id = data.get("sim_id")
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    if sim["status"] == "running":
        sim["status"] = "stopped"
        engine = sim.get("engine")
        if engine:
            engine.stop()

    return jsonify({"status": sim["status"]})


@dynamics_bp.route("/status/<sim_id>", methods=["GET"])
def status(sim_id: str):
    """Get simulation status."""
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    graph = sim["graph"]
    return jsonify({
        "sim_id": sim_id,
        "status": sim["status"],
        "timestep": graph._timestep,
        "num_nodes": len(graph._nodes),
        "num_edges": len(graph._edges),
        "templates": sim["templates"],
        "snapshot_count": _store.snapshot_count(sim_id),
        "event_count": len(sim["events"]),
        "error": sim.get("error"),
    })


# ---------------------------------------------------------------------------
# Metrics & events
# ---------------------------------------------------------------------------


@dynamics_bp.route("/metrics/<sim_id>", methods=["GET"])
def get_metrics(sim_id: str):
    """Return metric time series for a simulation.

    Optional query params:
        metric: str — filter to a single metric name
    """
    metric_name = request.args.get("metric")
    if metric_name:
        series = _store.get_metric_series(sim_id, metric_name)
        return jsonify({metric_name: series})

    # Return all available metrics
    available = _store.get_available_metrics(sim_id)
    result = {}
    for name in available:
        result[name] = _store.get_metric_series(sim_id, name)
    return jsonify(result)


@dynamics_bp.route("/events/<sim_id>", methods=["GET"])
def get_events(sim_id: str):
    """Return phase transition events."""
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    events = []
    for e in sim["events"]:
        if isinstance(e, dict):
            events.append(e)
        else:
            events.append({
                "timestep": e.timestep,
                "metric_name": e.metric_name,
                "event_type": e.event_type,
                "magnitude": e.magnitude,
                "description": e.description,
            })
    return jsonify(events)


# ---------------------------------------------------------------------------
# Manual intervention
# ---------------------------------------------------------------------------


@dynamics_bp.route("/inject-event", methods=["POST"])
def inject_event():
    """Inject a parameter shock into a running simulation.

    Expects JSON body with:
        sim_id:   str
        template: str — template name
        params:   dict — parameter overrides to apply
    """
    data = request.get_json(force=True)
    sim_id = data.get("sim_id")
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    engine = sim.get("engine")
    if not engine:
        return jsonify({"error": "no engine configured"}), 400

    template_name = data.get("template")
    params = data.get("params", {})
    engine.set_params(template_name, params)

    return jsonify({"status": "parameters updated", "template": template_name})


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@dynamics_bp.route("/export/<sim_id>/json", methods=["GET"])
def export_json(sim_id: str):
    """Export full simulation data as JSON.

    Returns all snapshots, metrics time series, and events.
    """
    sim = _get_sim(sim_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    snapshots = _store.load_all_snapshots(sim_id)
    available = _store.get_available_metrics(sim_id)
    metrics = {name: _store.get_metric_series(sim_id, name) for name in available}

    events_raw = sim.get("events", [])
    events = []
    for e in events_raw:
        if hasattr(e, "timestep"):
            events.append({
                "timestep": e.timestep,
                "metric_name": e.metric_name,
                "event_type": e.event_type,
                "magnitude": e.magnitude,
                "description": e.description,
            })
        elif isinstance(e, dict):
            events.append(e)

    payload = {
        "sim_id": sim_id,
        "snapshot_count": len(snapshots),
        "snapshots": [_snapshot_to_dict(s) for s in snapshots],
        "metrics": metrics,
        "events": events,
    }

    return Response(
        _json_dumps(payload),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=simulation_{sim_id}.json"},
    )


@dynamics_bp.route("/export/<sim_id>/csv", methods=["GET"])
def export_csv(sim_id: str):
    """Export metric time series as CSV.

    Each row is a timestep; columns are metric names.
    """
    available = _store.get_available_metrics(sim_id)
    if not available:
        return jsonify({"error": "no metrics found"}), 404

    series: dict[str, dict[int, float]] = {}
    all_timesteps: set[int] = set()
    for name in available:
        data = _store.get_metric_series(sim_id, name)
        series[name] = {ts: val for ts, val in data}
        all_timesteps.update(ts for ts, _ in data)

    timesteps = sorted(all_timesteps)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestep"] + available)
    for ts in timesteps:
        row = [ts] + [series[name].get(ts, "") for name in available]
        writer.writerow(row)

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=metrics_{sim_id}.csv"},
    )


# ---------------------------------------------------------------------------
# Scenario comparison
# ---------------------------------------------------------------------------


@dynamics_bp.route("/compare", methods=["POST"])
def compare():
    """Run two simulations with different parameters and compare metrics.

    Expects JSON body with:
        sim_id:    str — base simulation to fork
        params_a:  dict — parameter overrides for scenario A
        params_b:  dict — parameter overrides for scenario B
        steps:     int — number of steps to run each (default 100)
    """
    data = request.get_json(force=True)
    base_sim_id = data.get("sim_id")
    base_sim = _get_sim(base_sim_id)
    if not base_sim:
        return jsonify({"error": "base simulation not found"}), 404
    if not base_sim.get("engine"):
        return jsonify({"error": "base simulation not configured"}), 400

    params_a = data.get("params_a", {})
    params_b = data.get("params_b", {})
    steps = data.get("steps", 100)

    # Fork the base graph for both scenarios
    import copy
    base_snapshot = base_sim["graph"].snapshot()

    results = {}
    for label, params_override in [("a", params_a), ("b", params_b)]:
        from ..dynamics import DynamicsGraph
        fork_graph = DynamicsGraph(seed=base_snapshot)
        fork_id = uuid.uuid4().hex[:12]

        # Build engine with same templates but overridden params
        merged_params = copy.deepcopy(base_sim.get("params", {}))
        for tname, tparams in params_override.items():
            merged_params.setdefault(tname, {}).update(tparams)

        templates = []
        for tname in base_sim.get("templates", []):
            tcls = TEMPLATE_REGISTRY.get(tname)
            if tcls:
                templates.append(tcls())

        engine = SimulationEngine(
            graph=fork_graph,
            templates=templates,
            params=merged_params,
            seed=42,
            metrics_collector=MetricsCollector(),
        )

        snapshots = engine.run(steps)

        # Collect metric series
        metric_series: dict[str, list[tuple[int, float]]] = {}
        for snap in snapshots:
            for mname, mval in snap.metrics.items():
                metric_series.setdefault(mname, []).append((snap.timestep, mval))

        results[label] = {
            "sim_id": fork_id,
            "params": merged_params,
            "final_timestep": fork_graph.timestep,
            "final_metrics": snapshots[-1].metrics if snapshots else {},
            "metric_series": metric_series,
        }

    return jsonify({
        "status": "completed",
        "scenario_a": results["a"],
        "scenario_b": results["b"],
    })


# ---------------------------------------------------------------------------
# Demo data loading
# ---------------------------------------------------------------------------


@dynamics_bp.route("/demos", methods=["GET"])
def list_demos():
    """List available pre-run demo scenarios."""
    if not _DEMO_DATA_DIR.is_dir():
        return jsonify([])

    demos = []
    for d in sorted(_DEMO_DATA_DIR.iterdir()):
        meta_path = d / "metadata.json"
        if not meta_path.exists():
            continue
        with open(meta_path) as f:
            meta = _json_mod.load(f)
        demos.append({
            "name": meta.get("name", d.name),
            "description": meta.get("description", ""),
            "mode": meta.get("mode", ""),
            "num_nodes": meta.get("num_nodes", 0),
            "num_edges": meta.get("num_edges", 0),
            "steps": meta.get("steps", 0),
        })
    return jsonify(demos)


@dynamics_bp.route("/demo/<demo_name>/load", methods=["POST"])
def load_demo(demo_name: str):
    """Load a pre-run demo scenario.

    Reads the demo's initial graph, snapshots, metrics, and events
    from disk and registers them in the in-memory simulation registry
    so all existing graph/snapshot/metrics/events endpoints work.
    """
    demo_dir = _DEMO_DATA_DIR / demo_name
    if not demo_dir.is_dir():
        return jsonify({"error": f"demo '{demo_name}' not found"}), 404

    # Read all demo files
    with open(demo_dir / "metadata.json") as f:
        metadata = _json_mod.load(f)
    with open(demo_dir / "initial_graph.json") as f:
        initial_graph = _json_mod.load(f)
    with open(demo_dir / "snapshots.json") as f:
        snapshots = _json_mod.load(f)
    with open(demo_dir / "metrics.json") as f:
        metrics_data = _json_mod.load(f)
    with open(demo_dir / "events.json") as f:
        events_data = _json_mod.load(f)

    # Build a DynamicsGraph from the initial graph data
    from ..dynamics.models import GraphNode, GraphEdge, NodeState
    graph = DynamicsGraph()
    for n in initial_graph.get("nodes", []):
        state = NodeState(**n.get("state", {}))
        node = GraphNode(
            node_id=n["node_id"],
            node_type=n["node_type"],
            label=n["label"],
            state=state,
            institution_id=n.get("institution_id"),
            metadata=n.get("metadata", {}),
        )
        graph.add_node(node)
    for e in initial_graph.get("edges", []):
        edge = GraphEdge(
            edge_id=e["edge_id"],
            source_id=e["source_id"],
            target_id=e["target_id"],
            edge_type=e["edge_type"],
            weight=e.get("weight", 1.0),
            transfer_rate=e.get("transfer_rate", 0.1),
            metadata=e.get("metadata", {}),
        )
        graph.add_edge(edge)

    # Register as a simulation
    sim_id = f"demo_{demo_name}"
    total_steps = metadata.get("steps", 0)

    # Store snapshots and metrics in the DynamicsStore
    _store.delete_simulation(sim_id)
    for snap_dict in snapshots:
        ts = snap_dict["timestep"]
        snap_nodes = {}
        for nd in snap_dict.get("nodes", []):
            snap_nodes[nd["node_id"]] = GraphNode(
                node_id=nd["node_id"],
                node_type=nd["node_type"],
                label=nd["label"],
                state=NodeState(**nd.get("state", {})),
                institution_id=nd.get("institution_id"),
                metadata=nd.get("metadata", {}),
            )
        snap_edges = {}
        for ed in snap_dict.get("edges", []):
            snap_edges[ed["edge_id"]] = GraphEdge(
                edge_id=ed["edge_id"],
                source_id=ed["source_id"],
                target_id=ed["target_id"],
                edge_type=ed["edge_type"],
                weight=ed.get("weight", 1.0),
                transfer_rate=ed.get("transfer_rate", 0.1),
                metadata=ed.get("metadata", {}),
            )
        snap = GraphSnapshot(
            timestep=ts,
            nodes=snap_nodes,
            edges=snap_edges,
            metrics=snap_dict.get("metrics", {}),
        )
        _store.save_snapshot(sim_id, snap)

    # Also store per-timestep metrics for the time-series endpoint
    # The metrics.json has {metric_name: [value_at_t0, value_at_t1, ...]}
    import sqlite3
    with _store._connect() as conn:
        for metric_name, values in metrics_data.items():
            for timestep, value in enumerate(values):
                try:
                    conn.execute(
                        """INSERT OR REPLACE INTO metrics_timeseries
                           (sim_id, timestep, metric_name, metric_value)
                           VALUES (?, ?, ?, ?)""",
                        (sim_id, timestep, metric_name, float(value)),
                    )
                except (ValueError, TypeError):
                    pass

    # Set final timestep on graph
    graph._timestep = total_steps

    _simulations[sim_id] = {
        "graph": graph,
        "engine": None,
        "status": "completed",
        "templates": metadata.get("templates", []),
        "params": metadata.get("params", {}),
        "detector": PhaseTransitionDetector(),
        "events": events_data,
        "demo": True,
    }

    return jsonify({
        "sim_id": sim_id,
        "name": metadata.get("name"),
        "description": metadata.get("description"),
        "mode": metadata.get("mode"),
        "num_nodes": metadata.get("num_nodes", 0),
        "num_edges": metadata.get("num_edges", 0),
        "steps": total_steps,
        "snapshot_count": len(snapshots),
        "event_count": len(events_data),
    }), 201


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_dumps(obj: Any) -> str:
    """JSON serialize with compact formatting."""
    import json as _json
    return _json.dumps(obj, ensure_ascii=False, default=str)


def _snapshot_to_dict(snapshot: GraphSnapshot) -> dict[str, Any]:
    """Convert a GraphSnapshot to a JSON-serializable dict."""
    nodes = []
    for n in snapshot.nodes.values():
        nodes.append({
            "node_id": n.node_id,
            "node_type": n.node_type.value,
            "label": n.label,
            "institution_id": n.institution_id,
            "state": n.state.model_dump(),
            "metadata": n.metadata,
        })

    edges = []
    for e in snapshot.edges.values():
        edges.append({
            "edge_id": e.edge_id,
            "source_id": e.source_id,
            "target_id": e.target_id,
            "edge_type": e.edge_type.value,
            "weight": e.weight,
            "transfer_rate": e.transfer_rate,
            "metadata": e.metadata,
        })

    return {
        "timestep": snapshot.timestep,
        "nodes": nodes,
        "edges": edges,
        "metrics": snapshot.metrics,
        "timestamp": snapshot.timestamp.isoformat(),
    }
