"""Tests for the WO-5 mutation verification and certificate MVP."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.incidents import set_demo_agent
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.certificates import generate_certificate, verify_certificate_signature
from notary_platform.replay_engine.cassette import ResponseCassette
from notary_platform.snapshot import (
    CapturedElement,
    _compute_root_hash,
    _seal_element,
)

SECRET = b"test-secret-key-32-bytes-long!!!"
client = TestClient(app)


def _lending_agent(cassette: ResponseCassette, threshold: int = 700) -> str:
    result = cassette.lookup("POST", "https://api.example.com/credit-check")
    if result is None:
        return "UNKNOWN"
    score = result.get("response", {}).get("score", 0)
    return "APPROVE" if score >= threshold else "DENY"


def _make_snapshot_dict(score: int = 650) -> dict[str, Any]:
    elements = [
        {
            "kind": "http",
            "payload": {
                "request": {
                    "method": "POST",
                    "url": "https://api.example.com/credit-check",
                },
                "response": {"score": score},
                "status": 200,
            },
        },
        {
            "kind": "decision",
            "payload": {"decision": "DENY"},
        },
    ]
    prev_hash = b"\x00" * 32
    elem_hashes: list[bytes] = []
    sealed: list[dict[str, Any]] = []
    for e in elements:
        ce = CapturedElement(kind=e["kind"], payload=e.get("payload", {}))
        h = _seal_element(prev_hash, ce.canonical_bytes(), SECRET)
        elem_hashes.append(h)
        sealed.append({"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()})
        prev_hash = h
    root = _compute_root_hash(elem_hashes)
    return {
        "schema_version": 1,
        "timestamp": "2025-01-01T00:00:00Z",
        "elements": sealed,
        "merkle_chain": [h.hex() for h in elem_hashes],
        "root_hash": root,
    }


def _clear_storage() -> None:
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._certificates.clear()
    storage._counter = 0


class TestCertificateGeneration:
    def test_generates_valid_signature(self) -> None:
        cert = generate_certificate(
            incident_id="inc-000001",
            original_decision="DENY",
            mutated_decision="APPROVE",
            fix_config={"threshold": 620},
        )
        assert verify_certificate_signature(cert) is True

    def test_tampered_cert_fails(self) -> None:
        cert = generate_certificate(
            incident_id="inc-000001",
            original_decision="DENY",
            mutated_decision="APPROVE",
            fix_config={"threshold": 620},
        )
        cert["mutated_decision"] = "DENY"
        assert verify_certificate_signature(cert) is False

    def test_contains_replay_method(self) -> None:
        cert = generate_certificate(
            incident_id="inc-000001",
            original_decision="DENY",
            mutated_decision="APPROVE",
            fix_config={},
        )
        assert cert["replay_method"] == "sealed cassette replay"
        assert cert["certificate_type"] == "proof_of_mitigation"


class TestMutationEndpoint:
    def setup_method(self) -> None:
        _clear_storage()
        set_demo_agent(_lending_agent)

    def test_mutation_deny_to_approve(self) -> None:
        snap = _make_snapshot_dict(score=650)
        ingested = client.post("/v1/ingestion/snapshots", json={"snapshot": snap}).json()
        inc_id = ingested["incident_id"]

        resp = client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={"fix_config": {"threshold": 620}, "expected_correct_behavior": "APPROVE"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["original_decision"] == "DENY"
        assert data["mutated_decision"] == "APPROVE"
        assert data["mitigated"] is True

    def test_mutation_deny_to_deny_not_mitigated(self) -> None:
        snap = _make_snapshot_dict(score=650)
        ingested = client.post("/v1/ingestion/snapshots", json={"snapshot": snap}).json()
        inc_id = ingested["incident_id"]

        resp = client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={"fix_config": {"threshold": 900}, "expected_correct_behavior": "APPROVE"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["original_decision"] == "DENY"
        assert data["mutated_decision"] == "DENY"
        assert data["mitigated"] is False

    def test_mutation_404(self) -> None:
        resp = client.post(
            "/v1/incidents/inc-999999/mutation",
            json={"fix_config": {"threshold": 620}},
        )
        assert resp.status_code == 404

    def test_incident_status_becomes_mitigated(self) -> None:
        snap = _make_snapshot_dict(score=650)
        ingested = client.post("/v1/ingestion/snapshots", json={"snapshot": snap}).json()
        inc_id = ingested["incident_id"]

        client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={"fix_config": {"threshold": 620}},
        )
        resp = client.get(f"/v1/incidents/{inc_id}")
        assert resp.json()["status"] == "mitigated"


class TestCertificateEndpoint:
    def setup_method(self) -> None:
        _clear_storage()
        set_demo_agent(_lending_agent)

    def _mitigate_incident(self) -> str:
        snap = _make_snapshot_dict(score=650)
        ingested = client.post("/v1/ingestion/snapshots", json={"snapshot": snap}).json()
        inc_id = ingested["incident_id"]
        client.post(
            f"/v1/incidents/{inc_id}/mutation",
            json={"fix_config": {"threshold": 620}},
        )
        return inc_id

    def test_issue_certificate(self) -> None:
        inc_id = self._mitigate_incident()
        resp = client.post(f"/v1/certificates/{inc_id}")
        assert resp.status_code == 200
        cert = resp.json()
        assert cert["certificate_type"] == "proof_of_mitigation"
        assert cert["replay_method"] == "sealed cassette replay"
        assert cert["original_decision"] == "DENY"
        assert cert["mutated_decision"] == "APPROVE"
        assert cert["fix_config"] == {"threshold": 620}

    def test_certificate_only_when_mitigated(self) -> None:
        snap = _make_snapshot_dict(score=650)
        ingested = client.post("/v1/ingestion/snapshots", json={"snapshot": snap}).json()
        inc_id = ingested["incident_id"]
        resp = client.post(f"/v1/certificates/{inc_id}")
        assert resp.status_code == 409

    def test_get_certificate(self) -> None:
        inc_id = self._mitigate_incident()
        client.post(f"/v1/certificates/{inc_id}")
        resp = client.get(f"/v1/certificates/{inc_id}")
        assert resp.status_code == 200
        assert resp.json()["certificate_type"] == "proof_of_mitigation"

    def test_verify_certificate_signature(self) -> None:
        inc_id = self._mitigate_incident()
        client.post(f"/v1/certificates/{inc_id}")
        resp = client.get(f"/v1/certificates/{inc_id}/verify")
        assert resp.status_code == 200
        assert resp.json()["signature_valid"] is True

    def test_incident_status_becomes_certified(self) -> None:
        inc_id = self._mitigate_incident()
        client.post(f"/v1/certificates/{inc_id}")
        resp = client.get(f"/v1/incidents/{inc_id}")
        assert resp.json()["status"] == "certified"
