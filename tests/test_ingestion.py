"""Tests for the WO-3 ingestion endpoint and integrity verification."""

from __future__ import annotations

import base64
import sys

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.snapshot import (
    CapturedElement,
    ForensicSnapshot,
    _compute_root_hash,
    _seal_element,
    verify_snapshot,
)

SECRET = b"test-secret-key-32-bytes-long!!!"
client = TestClient(app)


def _make_snapshot_dict(elements: list[dict] | None = None) -> dict:
    if elements is None:
        elements = [
            {"kind": "llm", "payload": {"prompt": "hi"}},
            {"kind": "decision", "payload": {"decision": "approve"}},
        ]
    prev_hash = b"\x00" * 32
    elem_hashes: list[bytes] = []
    sealed_elements: list[dict] = []
    for e in elements:
        ce = CapturedElement(kind=e["kind"], payload=e.get("payload", {}))
        h = _seal_element(prev_hash, ce.canonical_bytes(), SECRET)
        elem_hashes.append(h)
        sealed_elements.append({"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()})
        prev_hash = h
    root = _compute_root_hash(elem_hashes)
    return {
        "schema_version": 1,
        "timestamp": "2025-01-01T00:00:00Z",
        "elements": sealed_elements,
        "merkle_chain": [h.hex() for h in elem_hashes],
        "root_hash": root,
    }


def _clear_storage() -> None:
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._certificates.clear()
    storage._evidence.clear()
    storage._counter = 0


class TestIngestion:
    def setup_method(self) -> None:
        _clear_storage()

    def test_ingest_valid_snapshot(self) -> None:
        snap_dict = _make_snapshot_dict()
        resp = client.post("/v1/incidents/ingest", json={"snapshot": snap_dict})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ingested"
        assert data["incident_id"].startswith("inc-")
        assert data["integrity"] == "not_verified_missing_key"
        assert "evidence_ref" in data

    def test_ingest_with_valid_key(self) -> None:
        snap_dict = _make_snapshot_dict()
        key_b64 = base64.b64encode(SECRET).decode()
        resp = client.post(
            "/v1/incidents/ingest",
            json={"snapshot": snap_dict, "secret_key_b64": key_b64},
        )
        assert resp.status_code == 200
        assert resp.json()["integrity"] == "verified"

    def test_ingest_tampered_snapshot_with_key(self) -> None:
        _clear_storage()
        snap_dict = _make_snapshot_dict()
        snap_dict["elements"][0]["payload"]["prompt"] = "tampered"
        key_b64 = base64.b64encode(SECRET).decode()
        resp = client.post(
            "/v1/incidents/ingest",
            json={"snapshot": snap_dict, "secret_key_b64": key_b64},
        )
        assert resp.status_code == 400

        # Verify empty incidents list
        assert client.get("/v1/incidents").json() == []

    def test_ingest_missing_fields(self) -> None:
        resp = client.post("/v1/incidents/ingest", json={"snapshot": {"schema_version": 1}})
        assert resp.status_code == 422

    def test_list_incidents(self) -> None:
        _clear_storage()
        snap_dict = _make_snapshot_dict()
        client.post("/v1/incidents/ingest", json={"snapshot": snap_dict})
        client.post("/v1/incidents/ingest", json={"snapshot": snap_dict})
        resp = client.get("/v1/incidents")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_incident(self) -> None:
        snap_dict = _make_snapshot_dict()
        ingested = client.post("/v1/incidents/ingest", json={"snapshot": snap_dict}).json()
        resp = client.get(f"/v1/incidents/{ingested['incident_id']}")
        assert resp.status_code == 200
        assert resp.json()["incident_id"] == ingested["incident_id"]
        # custody events were recorded
        assert any(c["action"] == "ingested" for c in resp.json()["custody"])

    def test_get_incident_404(self) -> None:
        resp = client.get("/v1/incidents/inc-999999")
        assert resp.status_code == 404

    def test_empty_list(self) -> None:
        _clear_storage()
        resp = client.get("/v1/incidents")
        assert resp.status_code == 200
        assert resp.json() == []


class TestVerifySnapshotFunction:
    def test_valid_snapshot(self) -> None:
        snap_dict = _make_snapshot_dict()
        snap = ForensicSnapshot.from_dict(snap_dict)
        assert verify_snapshot(snap, SECRET) is True

    def test_wrong_key(self) -> None:
        snap_dict = _make_snapshot_dict()
        snap = ForensicSnapshot.from_dict(snap_dict)
        assert verify_snapshot(snap, b"wrong-key-32-bytes-long!!!!!!!!!!") is False

    def test_empty_key(self) -> None:
        snap_dict = _make_snapshot_dict()
        snap = ForensicSnapshot.from_dict(snap_dict)
        assert verify_snapshot(snap, b"") is False


class TestNoCloudDependency:
    def test_no_cloud_modules(self) -> None:
        for mod in ("boto3", "requests", "openai", "anthropic"):
            if mod in sys.modules:
                del sys.modules[mod]

        import notary_platform.snapshot  # noqa: F401

        for mod in ("boto3", "openai", "anthropic"):
            assert mod not in sys.modules
