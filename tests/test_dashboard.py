"""Tests for the WO-6 minimal dashboard."""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.incidents import set_demo_agent
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.replay_engine.cassette import ResponseCassette

SECRET = b"test-secret-key-32-bytes-long!!!"
client = TestClient(app)


def _lending_agent(cassette: ResponseCassette, threshold: int = 700) -> str:
    result = cassette.lookup("POST", "https://api.example.com/credit-check")
    if result is None:
        return "UNKNOWN"
    score = result.get("response", {}).get("score", 0)
    return "APPROVE" if score >= threshold else "DENY"


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
        assert "Forensic Control Center" in resp.text

    def test_dashboard_empty(self) -> None:
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "Forensic Control Center" in resp.text

    def test_dashboard_shows_control_center_language(self) -> None:
        _clear_storage()
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "Forensic Control Center" in resp.text

        client.post("/v1/demo/lending-seed")
        resp = client.get("/dashboard")
        assert "Decision Path" in resp.text
        assert "Replay Proof" in resp.text
        assert "Fix Verification" in resp.text
        assert "Signed Proof" in resp.text
        assert "Credit API" in resp.text
        assert "failure point" in resp.text

    def test_seed_lending_demo(self) -> None:
        resp = client.post("/v1/demo/lending-seed", follow_redirects=False)
        assert resp.status_code == 303
        resp = client.get("/dashboard")
        assert "inc-" in resp.text

    def test_full_e2e_flow(self) -> None:
        set_demo_agent(_lending_agent)

        client.post("/v1/demo/lending-seed")
        incidents = client.get("/v1/incidents").json()
        assert len(incidents) == 1
        inc_id = incidents[0]["incident_id"]
        assert incidents[0]["status"] == "ingested"

        resp = client.post(f"/v1/incidents/{inc_id}/replay")
        assert resp.status_code == 200

        resp = client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={"fix_config": {"threshold": 620}},
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
