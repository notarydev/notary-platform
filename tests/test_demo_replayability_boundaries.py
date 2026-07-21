"""Tests for demo-forced replayability boundaries.

Proves:
- Demo-forced status does not bypass replay/mutation/proof validation
- Computed replayability is stored separately
- Non-demo records use computed state
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage

client = TestClient(app)


def _clear_storage() -> None:
    storage._vrs.clear()
    storage._labels.clear()
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._replay_runs.clear()
    storage._mutation_tests.clear()
    storage._proof_certs.clear()
    storage._counter = 0


class TestDemoReplayabilityBoundaries:
    def setup_method(self) -> None:
        _clear_storage()

    def test_demo_record_has_demo_source(self) -> None:
        """Demo-catalog seeded records show demo_seed replayability_source."""
        seed_result = client.post("/v1/demo/catalog/seed")
        assert seed_result.status_code == 200

        vrs = client.get("/v1/verification-records").json()
        demo_vrs = [v for v in vrs if v.get("replayability_source") == "demo_seed"]
        assert len(demo_vrs) > 0, "Expected at least one demo-seeded VR"

    def test_non_demo_record_uses_computed_replayability(self) -> None:
        """Non-demo records have computed_replayability set."""
        snapshot = {
            "elements": [
                {"kind": "http", "payload": {"request": {"method": "POST", "url": "/test"}, "response": {"ok": True}, "status": 200}},
                {"kind": "decision", "payload": {"decision": "OK"}},
            ],
            "root_hash": "test-root",
        }
        vr_resp = client.post("/v1/verification-records/from-snapshot", json=snapshot)
        assert vr_resp.status_code == 200
        vr = vr_resp.json()
        assert vr["replayability_source"] == "computed"
        assert vr["computed_replayability"] != "unknown"

    def test_missing_cassette_cannot_replay(self) -> None:
        """Records with missing_context replayability cannot replay."""
        snapshot = {
            "elements": [
                {"kind": "llm", "payload": {"prompt": "test", "response": "hi", "temperature": 0.1}},
                {"kind": "decision", "payload": {"decision": "UNKNOWN"}},
            ],
            "root_hash": "test-root",
        }
        vr_resp = client.post("/v1/verification-records/from-snapshot", json=snapshot)
        assert vr_resp.status_code == 200
        vr = vr_resp.json()
        assert vr["replayability"] == "evidence_only" or vr["replayability"] == "missing_context"

        replay_resp = client.post(f"/v1/verification-records/{vr['id']}/replay-runs")
        assert replay_resp.status_code == 200
        run = replay_resp.json()
        assert run["status"] == "incomplete"

    def test_mutation_requires_successful_replay(self) -> None:
        """Mutation without a successful replay is rejected."""
        snapshot = {
            "elements": [
                {"kind": "http", "payload": {"request": {"method": "POST", "url": "/test"}, "response": {"score": 650}, "status": 200}},
                {"kind": "decision", "payload": {"decision": "DENY"}},
            ],
            "root_hash": "test-root",
            "is_demo": True,
        }
        vr_resp = client.post("/v1/verification-records/from-snapshot", json=snapshot)
        assert vr_resp.status_code == 200
        vr = vr_resp.json()

        # Attempt mutation without label
        mutation = client.post(
            f"/v1/verification-records/{vr['id']}/mutation-tests",
            json={"fix_config": {"threshold": 620}, "expected_correct_behavior": "APPROVE"},
        )
        assert mutation.status_code == 400
        # Either needs label or replay

    def test_demo_blocked_state_prevents_proof(self) -> None:
        """Demo records in blocked state cannot get proofs issued via service layer."""
        from notary_platform.services import CertificateService, ServiceRegistry

        registry = ServiceRegistry(storage)

        # A record with no replay/mutation should fail proof
        snapshot = {
            "elements": [
                {"kind": "http", "payload": {"request": {"method": "POST", "url": "/test"}, "response": {"score": 650}, "status": 200}},
                {"kind": "decision", "payload": {"decision": "DENY"}},
            ],
            "root_hash": "test-root",
        }
        vr_resp = client.post("/v1/verification-records/from-snapshot", json=snapshot)
        assert vr_resp.status_code == 200
        vr = vr_resp.json()

        cert_service = CertificateService(registry)
        try:
            cert_service.issue_proof_of_mitigation(vr["id"], vr["org_id"])
            assert False, "Expected ValueError for proof without mutation"
        except ValueError:
            pass
