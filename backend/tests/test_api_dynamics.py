"""Tests for the dynamics API endpoints."""

import json

import pytest

from app import create_app


SAMPLE_GRAPH_DATA = {
    "graph_id": "test",
    "nodes": [
        {"uuid": "u1", "name": "Alice", "labels": ["Person"], "summary": "", "attributes": {}},
        {"uuid": "u2", "name": "Bob", "labels": ["Professor"], "summary": "", "attributes": {}},
        {"uuid": "u3", "name": "MIT", "labels": ["University"], "summary": "", "attributes": {}},
    ],
    "edges": [
        {
            "uuid": "e1", "name": "mentors", "fact": "Bob mentors Alice",
            "fact_type": "MENTORS", "source_node_uuid": "u2", "target_node_uuid": "u1",
            "attributes": {},
        },
    ],
}


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sim_id(client):
    """Initialize a simulation and return its sim_id."""
    resp = client.post(
        "/api/dynamics/initialize",
        data=json.dumps({"graph_data": SAMPLE_GRAPH_DATA}),
        content_type="application/json",
    )
    return resp.get_json()["sim_id"]


class TestInitialize:
    def test_returns_201(self, client):
        resp = client.post(
            "/api/dynamics/initialize",
            data=json.dumps({"graph_data": SAMPLE_GRAPH_DATA}),
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_returns_sim_id(self, client):
        resp = client.post(
            "/api/dynamics/initialize",
            data=json.dumps({"graph_data": SAMPLE_GRAPH_DATA}),
            content_type="application/json",
        )
        body = resp.get_json()
        assert "sim_id" in body
        assert body["num_nodes"] == 3
        assert body["num_edges"] == 1

    def test_suggests_templates(self, client):
        resp = client.post(
            "/api/dynamics/initialize",
            data=json.dumps({"graph_data": SAMPLE_GRAPH_DATA}),
            content_type="application/json",
        )
        body = resp.get_json()
        assert "diffusion" in body["suggested_templates"]

    def test_missing_graph_data(self, client):
        resp = client.post(
            "/api/dynamics/initialize",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestGraphState:
    def test_get_graph(self, client, sim_id):
        resp = client.get(f"/api/dynamics/graph/{sim_id}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["nodes"]) == 3

    def test_graph_not_found(self, client):
        resp = client.get("/api/dynamics/graph/nonexistent")
        assert resp.status_code == 404


class TestTemplates:
    def test_list_templates(self, client):
        resp = client.get("/api/dynamics/templates")
        assert resp.status_code == 200
        body = resp.get_json()
        names = {t["name"] for t in body}
        expected = {
            "diffusion", "opinion", "evolutionary", "resource", "feedback",
            "contagion", "game_theory", "network_evolution", "memory_landscape",
        }
        assert expected == names

    def test_get_parameters(self, client):
        resp = client.get("/api/dynamics/parameters/diffusion")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "transfer_rate" in body["parameters"]
        assert "priors" in body

    def test_get_parameters_not_found(self, client):
        resp = client.get("/api/dynamics/parameters/nonexistent")
        assert resp.status_code == 404


class TestConfigure:
    def test_configure_success(self, client, sim_id):
        resp = client.post(
            "/api/dynamics/configure",
            data=json.dumps({
                "sim_id": sim_id,
                "templates": ["diffusion"],
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "configured"

    def test_configure_unknown_template(self, client, sim_id):
        resp = client.post(
            "/api/dynamics/configure",
            data=json.dumps({
                "sim_id": sim_id,
                "templates": ["nonexistent"],
            }),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_configure_not_found(self, client):
        resp = client.post(
            "/api/dynamics/configure",
            data=json.dumps({"sim_id": "bad", "templates": ["diffusion"]}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestSimulationControl:
    def _configure(self, client, sim_id):
        client.post(
            "/api/dynamics/configure",
            data=json.dumps({"sim_id": sim_id, "templates": ["diffusion"]}),
            content_type="application/json",
        )

    def test_start_and_status(self, client, sim_id):
        self._configure(client, sim_id)
        resp = client.post(
            "/api/dynamics/start",
            data=json.dumps({"sim_id": sim_id, "steps": 5}),
            content_type="application/json",
        )
        assert resp.status_code == 200

        # Wait briefly for the simulation to finish
        import time
        time.sleep(0.5)

        resp = client.get(f"/api/dynamics/status/{sim_id}")
        body = resp.get_json()
        assert body["status"] in ("completed", "running")

    def test_start_without_configure(self, client, sim_id):
        resp = client.post(
            "/api/dynamics/start",
            data=json.dumps({"sim_id": sim_id, "steps": 5}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_stop(self, client, sim_id):
        self._configure(client, sim_id)
        client.post(
            "/api/dynamics/start",
            data=json.dumps({"sim_id": sim_id, "steps": 1000}),
            content_type="application/json",
        )
        resp = client.post(
            "/api/dynamics/stop",
            data=json.dumps({"sim_id": sim_id}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_status_not_found(self, client):
        resp = client.get("/api/dynamics/status/nonexistent")
        assert resp.status_code == 404


class TestMetricsAndEvents:
    def _run_sim(self, client, sim_id, steps=10):
        client.post(
            "/api/dynamics/configure",
            data=json.dumps({"sim_id": sim_id, "templates": ["diffusion"]}),
            content_type="application/json",
        )
        client.post(
            "/api/dynamics/start",
            data=json.dumps({"sim_id": sim_id, "steps": steps}),
            content_type="application/json",
        )
        import time
        time.sleep(1)

    def test_get_metrics(self, client, sim_id):
        self._run_sim(client, sim_id)
        resp = client.get(f"/api/dynamics/metrics/{sim_id}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert isinstance(body, dict)

    def test_get_events(self, client, sim_id):
        self._run_sim(client, sim_id)
        resp = client.get(f"/api/dynamics/events/{sim_id}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert isinstance(body, list)


class TestInjectEvent:
    def test_inject_params(self, client, sim_id):
        client.post(
            "/api/dynamics/configure",
            data=json.dumps({"sim_id": sim_id, "templates": ["diffusion"]}),
            content_type="application/json",
        )
        resp = client.post(
            "/api/dynamics/inject-event",
            data=json.dumps({
                "sim_id": sim_id,
                "template": "diffusion",
                "params": {"transfer_rate": 0.5},
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200


class TestExport:
    def _run_sim(self, client, sim_id, steps=10):
        client.post(
            "/api/dynamics/configure",
            data=json.dumps({"sim_id": sim_id, "templates": ["diffusion"]}),
            content_type="application/json",
        )
        client.post(
            "/api/dynamics/start",
            data=json.dumps({"sim_id": sim_id, "steps": steps}),
            content_type="application/json",
        )
        import time
        time.sleep(1)

    def test_export_json(self, client, sim_id):
        self._run_sim(client, sim_id)
        resp = client.get(f"/api/dynamics/export/{sim_id}/json")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        data = json.loads(resp.data)
        assert "sim_id" in data
        assert "snapshots" in data
        assert "metrics" in data

    def test_export_csv(self, client, sim_id):
        self._run_sim(client, sim_id)
        resp = client.get(f"/api/dynamics/export/{sim_id}/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        text = resp.data.decode("utf-8")
        lines = text.strip().split("\n")
        assert len(lines) > 1  # header + at least one data row
        assert "timestep" in lines[0]

    def test_export_not_found(self, client):
        resp = client.get("/api/dynamics/export/nonexistent/json")
        assert resp.status_code == 404


class TestCompare:
    def test_compare_scenarios(self, client, sim_id):
        # Configure the base simulation
        client.post(
            "/api/dynamics/configure",
            data=json.dumps({"sim_id": sim_id, "templates": ["diffusion"]}),
            content_type="application/json",
        )
        resp = client.post(
            "/api/dynamics/compare",
            data=json.dumps({
                "sim_id": sim_id,
                "params_a": {"diffusion": {"transfer_rate": 0.01}},
                "params_b": {"diffusion": {"transfer_rate": 0.5}},
                "steps": 10,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "completed"
        assert "scenario_a" in body
        assert "scenario_b" in body
        assert "metric_series" in body["scenario_a"]

    def test_compare_not_found(self, client):
        resp = client.post(
            "/api/dynamics/compare",
            data=json.dumps({"sim_id": "bad", "params_a": {}, "params_b": {}}),
            content_type="application/json",
        )
        assert resp.status_code == 404
