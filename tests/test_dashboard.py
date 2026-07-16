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

    def test_dashboard_default_is_customer_service_handoff(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Customer-service failed handoff" in resp.text
        assert "Scenario Intelligence" in resp.text
        assert "Claim Scope" in resp.text
        assert "fully replayable from sealed cassette" in resp.text
        assert "customer-approved expected outcome" in resp.text
        assert "Replayability Status" in resp.text
        assert "Label Provenance" in resp.text
        assert "Cassette" in resp.text
        assert "Sandbox" in resp.text
        assert "Production" in resp.text

    def test_dashboard_shows_control_center_language(self) -> None:
        _clear_storage()
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "FORENSIC CONTROL CENTER" in resp.text
        assert "Decision graph" in resp.text
        assert "Scenario Intelligence" in resp.text
        assert "Claim Scope" in resp.text
        assert "Cassette" in resp.text
        assert "Sandbox" in resp.text
        assert "Production" in resp.text

        client.post(
            "/v1/demo/lending-seed?scenario_id=customer-service-handoff",
            follow_redirects=False,
        )
        resp = client.get("/dashboard?scenario_id=customer-service-handoff")
        assert "Replay failure" in resp.text

    def test_dashboard_empty(self) -> None:
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "FORENSIC CONTROL CENTER" in resp.text

    def test_dashboard_has_four_scenarios(self) -> None:
        resp = client.get("/dashboard")
        assert "Customer-service failed handoff" in resp.text
        assert "Qualified borrower denied" in resp.text
        assert "Necessary care auto-denied" in resp.text
        assert "Qualified candidate rejected" in resp.text

    def test_dashboard_proof_scope_language(self) -> None:
        resp = client.get("/dashboard")
        assert "Claim Scope" in resp.text
        assert "does not certify general AI safety" in resp.text
        assert "customer-approved expected outcome" in resp.text
        assert "demo data / dev signing" in resp.text
        assert "fully replayable from sealed cassette" in resp.text

    def test_dashboard_mitigated_proof_wording(self) -> None:
        client.post("/v1/demo/lending-seed?scenario_id=lending-denial")
        inc_id = client.get("/v1/incidents").json()[0]["incident_id"]
        client.post(f"/v1/incidents/{inc_id}/replay")
        client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={"fix_config": {"threshold": 620}, "expected_correct_behavior": "APPROVE"},
        )
        resp = client.get("/dashboard?scenario_id=lending-denial")
        assert "Verified for this scenario" in resp.text

        client.post(f"/v1/certificates/{inc_id}")
        resp = client.get("/dashboard?scenario_id=lending-denial")
        assert "Proof issued for tested scenario" in resp.text

    def test_dashboard_scenario_intelligence(self) -> None:
        resp = client.get("/dashboard?scenario_id=lending-denial")
        assert "Scenario Intelligence" in resp.text
        assert "12,482" not in resp.text
        assert "9,310 lending underwriting decisions" in resp.text
        assert "ECOA / Fair Lending" in resp.text

    def test_seed_lending_demo(self) -> None:
        resp = client.post("/v1/demo/lending-seed", follow_redirects=False)
        assert resp.status_code == 303
        resp = client.get("/dashboard")
        assert "inc-" in resp.text

    def test_environment_toggle_changes_copy(self) -> None:
        assert "Active default. Replay uses sealed recorded responses." in client.get(
            "/dashboard?mode=cassette"
        ).text
        assert "No sandbox calls in this prototype." in client.get(
            "/dashboard?mode=sandbox"
        ).text
        assert "Capture source only. Notary never replays or tests fixes against production." in client.get(
            "/dashboard?mode=production"
        ).text

    def test_seed_each_scenario(self) -> None:
        _clear_storage()

        for scenario_id in [
            "customer-service-handoff",
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
        assert len(incidents) == 4

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

    def test_full_e2e_flow_customer_service_handoff(self) -> None:
        client.post("/v1/demo/lending-seed?scenario_id=customer-service-handoff")
        incidents = client.get("/v1/incidents").json()
        assert len(incidents) == 1
        inc_id = incidents[0]["incident_id"]
        assert incidents[0]["status"] == "ingested"

        resp = client.post(f"/v1/incidents/{inc_id}/replay")
        assert resp.status_code == 200
        assert resp.json()["decision"] == "CONTINUE_BOT"

        resp = client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={
                "fix_config": {"escalate_after_repeated_human_request": True},
                "expected_correct_behavior": "ESCALATE_TO_HUMAN",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["mitigated"] is True
        assert resp.json()["mutated_decision"] == "ESCALATE_TO_HUMAN"

        resp = client.post(f"/v1/certificates/{inc_id}")
        assert resp.status_code == 200
        assert resp.json()["replay_method"] == "sealed cassette replay"

        resp = client.get(f"/v1/certificates/{inc_id}/verify")
        assert resp.json()["signature_valid"] is True

        resp = client.get(f"/v1/incidents/{inc_id}")
        assert resp.json()["status"] == "certified"
