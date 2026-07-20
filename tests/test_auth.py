"""Tests for authentication, org scoping, and the remote-storage guard (WO-3/17/23/24)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform import config
from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage

client = TestClient(app)


def _clear_storage() -> None:
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._certificates.clear()
    storage._evidence.clear()
    storage._counter = 0


def _reload_settings(auth_token: str = "") -> None:
    # Settings is module-level mutable; auth reads it at call time.
    config.SETTINGS.api_auth_token = auth_token


class TestAuthDisabledByDefault:
    def setup_method(self) -> None:
        _clear_storage()
        _reload_settings("")

    def test_unauthenticated_list_when_disabled(self) -> None:
        resp = client.get("/v1/incidents")
        assert resp.status_code == 200


class TestAuthEnforced:
    def setup_method(self) -> None:
        _clear_storage()
        _reload_settings("secret-token")

    def teardown_method(self) -> None:
        _reload_settings("")

    def test_missing_token_rejected(self) -> None:
        resp = client.get("/v1/incidents")
        assert resp.status_code == 401

    def test_wrong_token_rejected(self) -> None:
        resp = client.get("/v1/incidents", headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401

    def test_valid_bearer_accepted(self) -> None:
        resp = client.get("/v1/incidents", headers={"Authorization": "Bearer secret-token"})
        assert resp.status_code == 200

    def test_x_api_key_accepted(self) -> None:
        resp = client.get("/v1/incidents", headers={"x-api-key": "secret-token"})
        assert resp.status_code == 200


class TestOrgScoping:
    def setup_method(self) -> None:
        _clear_storage()
        _reload_settings("secret-token")

    def teardown_method(self) -> None:
        _reload_settings("")

    def test_cross_org_access_denied(self) -> None:
        from notary_platform.snapshot import (
            CapturedElement,
            _compute_root_hash,
            _seal_element,
        )

        prev = b"\x00" * 32
        ce = CapturedElement(kind="decision", payload={"decision": "x"})
        h = _seal_element(prev, ce.canonical_bytes(), b"k" * 32)
        snap = {
            "schema_version": 1,
            "timestamp": "t",
            "elements": [{"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()}],
            "merkle_chain": [h.hex()],
            "root_hash": _compute_root_hash([h]),
        }
        # Ingest under org "acme".
        r = client.post(
            "/v1/incidents/ingest",
            headers={"Authorization": "Bearer secret-token", "X-Notary-Org": "acme"},
            json={"snapshot": snap},
        )
        assert r.status_code == 200
        inc_id = r.json()["incident_id"]

        # A different org cannot read it.
        r2 = client.get(
            f"/v1/incidents/{inc_id}",
            headers={"Authorization": "Bearer secret-token", "X-Notary-Org": "other"},
        )
        assert r2.status_code == 404

        # The owning org can.
        r3 = client.get(
            f"/v1/incidents/{inc_id}",
            headers={"Authorization": "Bearer secret-token", "X-Notary-Org": "acme"},
        )
        assert r3.status_code == 200

    def test_body_org_id_cannot_override_authenticated_org(self) -> None:
        from notary_platform.snapshot import (
            CapturedElement,
            _compute_root_hash,
            _seal_element,
        )

        prev = b"\x00" * 32
        ce = CapturedElement(kind="decision", payload={"decision": "x"})
        h = _seal_element(prev, ce.canonical_bytes(), b"k" * 32)
        snap = {
            "schema_version": 1,
            "timestamp": "t",
            "elements": [{"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()}],
            "merkle_chain": [h.hex()],
            "root_hash": _compute_root_hash([h]),
        }

        r = client.post(
            "/v1/incidents/ingest",
            headers={"Authorization": "Bearer secret-token", "X-Notary-Org": "acme"},
            json={"snapshot": snap, "org_id": "other"},
        )
        assert r.status_code == 200
        assert r.json()["org_id"] == "acme"
        inc_id = r.json()["incident_id"]

        assert client.get(
            f"/v1/incidents/{inc_id}",
            headers={"Authorization": "Bearer secret-token", "X-Notary-Org": "other"},
        ).status_code == 404
        assert client.get(
            f"/v1/incidents/{inc_id}",
            headers={"Authorization": "Bearer secret-token", "X-Notary-Org": "acme"},
        ).status_code == 200
