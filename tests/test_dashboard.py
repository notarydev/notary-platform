"""Tests for the Phase 1 Forensic Control Center dashboard."""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage

client = TestClient(app)


def _clear_storage() -> None:
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._certificates.clear()
    storage._counter = 0


class TestHealth:
    def test_health(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestDashboard:
    def setup_method(self) -> None:
        _clear_storage()

    def test_index(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "FORENSIC CONTROL CENTER" in resp.text

    def test_dashboard_shows_control_center_language(self) -> None:
        _clear_storage()
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "FORENSIC CONTROL CENTER" in resp.text
        assert "Decision graph" in resp.text
        assert "Cassette" in resp.text
        assert "Sandbox" in resp.text
        assert "Production" in resp.text

        client.post("/v1/demo/lending-seed")
        resp = client.get("/dashboard")
        assert "Replay failure" in resp.text

    def test_dashboard_empty(self) -> None:
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "FORENSIC CONTROL CENTER" in resp.text

    def test_dashboard_has_three_scenarios(self) -> None:
        resp = client.get("/dashboard")
        assert "Qualified borrower denied" in resp.text
        assert "Necessary care auto-denied" in resp.text
        assert "Qualified candidate rejected" in resp.text

    def test_seed_lending_demo(self) -> None:
        resp = client.post("/v1/demo/lending-seed", follow_redirects=False)
        assert resp.status_code == 303
        resp = client.get("/dashboard")
        assert "inc-" in resp.text

    def test_seed_each_scenario(self) -> None:
        _clear_storage()

        for scenario_id in [
            "lending-denial",
            "prior-auth-denial",
            "hiring-screen-rejection",
        ]:
            resp = client.post(
                f"/v1/demo/lending-seed?scenario_id={scenario_id}",
                follow_redirects=False,
            )
            assert resp.status_code == 303

        incidents = client.get("/v1/incidents").json()
        assert len(incidents) == 3

    def test_environment_toggle_changes_copy(self) -> None:
        assert "Cassette mode is the active prototype path" in client.get(
            "/dashboard?mode=cassette"
        ).text
        assert "Sandbox mode shows where a real provider" in client.get(
            "/dashboard?mode=sandbox"
        ).text
        assert "Production mode shows where the original decision" in client.get(
            "/dashboard?mode=production"
        ).text

    def test_full_e2e_flow_lending(self) -> None:
        client.post("/v1/demo/lending-seed?scenario_id=lending-denial")
        incidents = client.get("/v1/incidents").json()
        assert len(incidents) == 1
        inc_id = incidents[0]["incident_id"]
        assert incidents[0]["status"] == "ingested"

        resp = client.post(f"/v1/incidents/{inc_id}/replay")
        assert resp.status_code == 200

        resp = client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={"fix_config": {"threshold": 620}, "expected_correct_behavior": "APPROVE"},
        )
        assert resp.status_code == 200
        assert resp.json()["mitigated"] is True

        resp = client.post(f"/v1/certificates/{inc_id}")
        assert resp.status_code == 200
        assert resp.json()["replay_method"] == "sealed cassette replay"

        resp = client.get(f"/v1/certificates/{inc_id}/verify")
        assert resp.json()["signature_valid"] is True

        resp = client.get(f"/v1/incidents/{inc_id}")
        assert resp.json()["status"] == "certified"
