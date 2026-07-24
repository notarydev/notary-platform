"""Conformance tests for DEP ingress — single, batch, and CloudEvent ingestion.

Covers:
  - POST /v1/dep/resources (accept, duplicate, reject, quarantine)
  - POST /v1/dep/batches
  - POST /v1/dep/cloudevents
  - GET  /v1/dep/resources/{id}
  - GET  /v1/discovery/sources
  - POST /v1/discovery/providers
  - GET  /v1/discovery/providers/{id}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.dep_ingress import storage
from notary_platform.dep.canonical import compute_digest

client = TestClient(app)

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dep" / "valid"
_VALID_FIXTURES = sorted(_FIXTURES.glob("*.json")) if _FIXTURES.is_dir() else []


def _load_fixture(name: str) -> dict[str, Any]:
    path = _FIXTURES / name
    if not path.exists():
        msg = f"Fixture not found: {path}"
        raise FileNotFoundError(msg)
    with open(path, "r") as f:
        return json.load(f)


def _make_envelope() -> dict[str, Any]:
    if _VALID_FIXTURES:
        return _load_fixture(_VALID_FIXTURES[0].name)
    return {
        "id": "env-001",
        "version": "0.1.0",
        "resource": {
            "id": "res-test-001",
            "type": "audit_log",
            "provider_id": "prov-001",
            "collected_at": "2025-06-01T00:00:00Z",
        },
        "digest": {"algorithm": "sha256", "value": ""},
    }


def _fix_digest(envelope: dict[str, Any]) -> dict[str, Any]:
    envelope["digest"]["value"] = compute_digest(envelope)
    return envelope


# ── Helpers ──


def _reset_storage() -> None:
    # Private dicts on the concrete MemoryStorage — safe in test code.
    storage._resources.clear()  # type: ignore[attr-defined]
    storage._integrity_conflicts.clear()  # type: ignore[attr-defined]
    storage._providers.clear()  # type: ignore[attr-defined]
    storage._payloads.clear()  # type: ignore[attr-defined]


# ═══════════════════════════════════════════════════════════════════════════════
# POST /v1/dep/resources
# ═══════════════════════════════════════════════════════════════════════════════


class TestIngestResource:
    def setup_method(self) -> None:
        _reset_storage()

    def test_accept_valid_envelope(self) -> None:
        env = _fix_digest(_make_envelope())
        resp = client.post("/v1/dep/resources", json=env)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["resource_id"] == env["resource"]["id"]

    def test_reject_invalid_envelope(self) -> None:
        resp = client.post("/v1/dep/resources", json={"bad": "data"})
        assert resp.status_code == 422, resp.text
        data = resp.json()
        assert "detail" in data

    def test_reject_missing_resource_id(self) -> None:
        env = _fix_digest(_make_envelope())
        env["resource"] = {"type": "audit_log"}
        resp = client.post("/v1/dep/resources", json=env)
        assert resp.status_code == 422, resp.text

    def test_duplicate_envelope(self) -> None:
        env = _fix_digest(_make_envelope())
        resp1 = client.post("/v1/dep/resources", json=env)
        assert resp1.status_code == 200
        resp2 = client.post("/v1/dep/resources", json=env)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate"

    def test_quarantine_on_digest_mismatch(self) -> None:
        env = _fix_digest(_make_envelope())
        resp1 = client.post("/v1/dep/resources", json=env)
        assert resp1.status_code == 200

        # Same resource.id but different content → must re-digest to pass validation
        env["resource"]["provider_id"] = "prov-different"
        env["digest"]["value"] = compute_digest(env)
        resp2 = client.post("/v1/dep/resources", json=env)
        assert resp2.status_code == 409, resp2.text
        data = resp2.json()
        assert data["detail"]["status"] == "quarantined"

    def test_get_resource(self) -> None:
        env = _fix_digest(_make_envelope())
        client.post("/v1/dep/resources", json=env)
        rid = env["resource"]["id"]
        resp = client.get(f"/v1/dep/resources/{rid}")
        assert resp.status_code == 200
        assert resp.json()["resource_id"] == rid

    def test_get_resource_not_found(self) -> None:
        resp = client.get("/v1/dep/resources/nonexistent")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# POST /v1/dep/batches
# ═══════════════════════════════════════════════════════════════════════════════


class TestIngestBatch:
    def setup_method(self) -> None:
        _reset_storage()

    def test_batch_accepted(self) -> None:
        e1 = _fix_digest({**_make_envelope(), "id": "batch-env-1", "resource": {**_make_envelope()["resource"], "id": "res-batch-1"}})
        e2 = _fix_digest({**_make_envelope(), "id": "batch-env-2", "resource": {**_make_envelope()["resource"], "id": "res-batch-2"}})
        resp = client.post("/v1/dep/batches", json={"envelopes": [e1, e2]})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 2
        assert data["accepted"] == 2

    def test_batch_empty_rejected(self) -> None:
        resp = client.post("/v1/dep/batches", json={"envelopes": []})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /v1/dep/cloudevents
# ═══════════════════════════════════════════════════════════════════════════════


class TestIngestCloudEvent:
    def setup_method(self) -> None:
        _reset_storage()

    def test_cloudevent_with_data(self) -> None:
        env = _fix_digest(_make_envelope())
        ce = {
            "id": "ce-001",
            "source": "/test",
            "specversion": "1.0",
            "type": "dep.resource",
            "data": env,
        }
        resp = client.post("/v1/dep/cloudevents", json=ce)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "accepted"

    def test_cloudevent_with_data_base64(self) -> None:
        import base64

        env = _fix_digest(_make_envelope())
        raw = json.dumps(env).encode("utf-8")
        ce = {
            "id": "ce-002",
            "source": "/test",
            "specversion": "1.0",
            "type": "dep.resource",
            "data_base64": base64.b64encode(raw).decode("ascii"),
        }
        resp = client.post("/v1/dep/cloudevents", json=ce)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "accepted"

    def test_cloudevent_missing_data(self) -> None:
        ce = {"id": "ce-003", "source": "/test", "specversion": "1.0", "type": "dep.resource"}
        resp = client.post("/v1/dep/cloudevents", json=ce)
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /v1/discovery/sources
# ═══════════════════════════════════════════════════════════════════════════════


class TestDiscoverySources:
    def setup_method(self) -> None:
        _reset_storage()

    def test_list_sources_empty(self) -> None:
        resp = client.get("/v1/discovery/sources")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_sources_after_ingest(self) -> None:
        env = _fix_digest(_make_envelope())
        client.post("/v1/dep/resources", json=env)
        resp = client.get("/v1/discovery/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["resource_id"] == env["resource"]["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# POST /v1/discovery/providers
# ═══════════════════════════════════════════════════════════════════════════════


class TestProviders:
    def setup_method(self) -> None:
        _reset_storage()

    def test_register_provider(self) -> None:
        body = {"provider_id": "prov-001", "name": "Test Provider", "provider_type": "sdk"}
        resp = client.post("/v1/discovery/providers", json=body)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["provider_id"] == "prov-001"
        assert data["name"] == "Test Provider"

    def test_register_duplicate_provider(self) -> None:
        body = {"provider_id": "prov-001", "name": "Test", "provider_type": "sdk"}
        client.post("/v1/discovery/providers", json=body)
        resp = client.post("/v1/discovery/providers", json=body)
        assert resp.status_code == 409

    def test_get_provider(self) -> None:
        body = {"provider_id": "prov-002", "name": "Another", "provider_type": "platform"}
        client.post("/v1/discovery/providers", json=body)
        resp = client.get("/v1/discovery/providers/prov-002")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Another"

    def test_get_provider_not_found(self) -> None:
        resp = client.get("/v1/discovery/providers/nonexistent")
        assert resp.status_code == 404
