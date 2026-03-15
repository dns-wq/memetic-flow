"""
SQLite persistence for dynamics graph snapshots and metric time series.

Stores graph state alongside the existing OASIS trace database so that
simulation history can be replayed and metrics can be queried for
visualization without holding everything in memory.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from .models import GraphEdge, GraphNode, GraphSnapshot, NodeState


_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id      TEXT    NOT NULL,
    timestep    INTEGER NOT NULL,
    nodes_json  TEXT    NOT NULL,
    edges_json  TEXT    NOT NULL,
    institutions_json TEXT NOT NULL,
    metrics_json TEXT   NOT NULL DEFAULT '{}',
    created_at  TEXT    NOT NULL,
    UNIQUE(sim_id, timestep)
);

CREATE TABLE IF NOT EXISTS metrics_timeseries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id      TEXT    NOT NULL,
    timestep    INTEGER NOT NULL,
    metric_name TEXT    NOT NULL,
    metric_value REAL   NOT NULL,
    UNIQUE(sim_id, timestep, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_sim
    ON snapshots(sim_id, timestep);
CREATE INDEX IF NOT EXISTS idx_metrics_sim
    ON metrics_timeseries(sim_id, timestep);
"""


class DynamicsStore:
    """SQLite-backed persistence for graph snapshots and metrics."""

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_dir = os.path.join(os.path.dirname(__file__), "../../data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "dynamics.db")
        self._db_path = db_path
        self._init_db()

    # ------------------------------------------------------------------
    # Snapshot CRUD
    # ------------------------------------------------------------------

    def save_snapshot(self, sim_id: str, snap: GraphSnapshot) -> None:
        nodes_json = json.dumps(
            {k: v.model_dump() for k, v in snap.nodes.items()},
            ensure_ascii=False,
        )
        edges_json = json.dumps(
            {k: v.model_dump() for k, v in snap.edges.items()},
            ensure_ascii=False,
        )
        institutions_json = json.dumps(snap.institutions, ensure_ascii=False)
        metrics_json = json.dumps(snap.metrics, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshots
                    (sim_id, timestep, nodes_json, edges_json,
                     institutions_json, metrics_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sim_id,
                    snap.timestep,
                    nodes_json,
                    edges_json,
                    institutions_json,
                    metrics_json,
                    snap.timestamp.isoformat(),
                ),
            )

            # Also fan out metrics into the time-series table
            for name, value in snap.metrics.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO metrics_timeseries
                        (sim_id, timestep, metric_name, metric_value)
                    VALUES (?, ?, ?, ?)
                    """,
                    (sim_id, snap.timestep, name, value),
                )

    def load_snapshot(
        self, sim_id: str, timestep: int
    ) -> GraphSnapshot | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE sim_id=? AND timestep=?",
                (sim_id, timestep),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_snapshot(row)

    def load_latest_snapshot(self, sim_id: str) -> GraphSnapshot | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE sim_id=? ORDER BY timestep DESC LIMIT 1",
                (sim_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_snapshot(row)

    def load_all_snapshots(self, sim_id: str) -> list[GraphSnapshot]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM snapshots WHERE sim_id=? ORDER BY timestep",
                (sim_id,),
            ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def snapshot_count(self, sim_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM snapshots WHERE sim_id=?", (sim_id,)
            ).fetchone()
        return row[0]

    # ------------------------------------------------------------------
    # Metric time-series queries
    # ------------------------------------------------------------------

    def get_metric_series(
        self, sim_id: str, metric_name: str
    ) -> list[tuple[int, float]]:
        """Return ``[(timestep, value), ...]`` for a single metric."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT timestep, metric_value
                FROM metrics_timeseries
                WHERE sim_id=? AND metric_name=?
                ORDER BY timestep
                """,
                (sim_id, metric_name),
            ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def get_all_metrics_at(
        self, sim_id: str, timestep: int
    ) -> dict[str, float]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT metric_name, metric_value
                FROM metrics_timeseries
                WHERE sim_id=? AND timestep=?
                """,
                (sim_id, timestep),
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def get_available_metrics(self, sim_id: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT metric_name FROM metrics_timeseries WHERE sim_id=?",
                (sim_id,),
            ).fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def delete_simulation(self, sim_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM snapshots WHERE sim_id=?", (sim_id,))
            conn.execute(
                "DELETE FROM metrics_timeseries WHERE sim_id=?", (sim_id,)
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row) -> GraphSnapshot:
        nodes_raw: dict[str, Any] = json.loads(row["nodes_json"])
        edges_raw: dict[str, Any] = json.loads(row["edges_json"])

        nodes = {k: GraphNode(**v) for k, v in nodes_raw.items()}
        edges = {k: GraphEdge(**v) for k, v in edges_raw.items()}
        institutions = json.loads(row["institutions_json"])
        metrics = json.loads(row["metrics_json"])

        return GraphSnapshot(
            timestep=row["timestep"],
            nodes=nodes,
            edges=edges,
            institutions=institutions,
            metrics=metrics,
            timestamp=datetime.fromisoformat(row["created_at"]),
        )
