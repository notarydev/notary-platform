"""Tenant isolation tests for DEP ingress and discovery.

Each test validates that an org cannot read or act upon resources belonging to
another org.  Uses the ``X-Notary-Org`` header to simulate multi-tenant
scenarios.
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
        raise FileNotFoundError(f"Fixture not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def _make_envelope() -> dict[str, Any]:
    if _VALID_FIXTURES:
        return _load_fixture(_VALID_FIXTURES[0].name)
    return {
        "id": "env-iso-001",
        "version": "0.1.0",
        "resource": {
            "id": "res-iso-001",
            "type": "audit_log",
            "provider_id": "prov-iso-001",
            "collected_at": "2025-06-01T00:00:00Z",
        },
        "digest": {"algorithm": "sha256", "value": ""},
    }


def _make_custom_envelope(resource_id: str, envelope_id: str = "") -> dict[str, Any]:
    env = _make_envelope()
    env["resource"]["id"] = resource_id
    if envelope_id:
        env["id"] = envelope_id
    env["digest"]["value"] = compute_digest(env)
    return env


def _reset_storage() -> None:
    # Private dicts on the concrete MemoryStorage — safe in test code.
    storage._resources.clear()  # type: ignore[attr-defined]
    storage._integrity_conflicts.clear()  # type: ignore[attr-defined]
    storage._providers.clear()  # type: ignore[attr-defined]
    storage._payloads.clear()  # type: ignore[attr-defined]


_ORG_A = "org-alice"
_ORG_B = "org-bob"


class TestIngressTenantIsolation:
    def setup_method(self) -> None:
        _reset_storage()

    def test_org_a_cannot_see_org_b_resource(self) -> None:
        env = _make_custom_envelope("res-iso-010")
        client.post("/v1/dep/resources", json=env, headers={"X-Notary-Org": _ORG_A})

        resp = client.get(
            "/v1/dep/resources/res-iso-010",
            headers={"X-Notary-Org": _ORG_B},
        )
        assert resp.status_code == 404

    def test_org_a_can_see_own_resource(self) -> None:
        env = _make_custom_envelope("res-iso-020")
        client.post("/v1/dep/resources", json=env, headers={"X-Notary-Org": _ORG_A})

        resp = client.get(
            "/v1/dep/resources/res-iso-020",
            headers={"X-Notary-Org": _ORG_A},
        )
        assert resp.status_code == 200
        assert resp.json()["resource_id"] == "res-iso-020"

    def test_sources_list_is_scoped(self) -> None:
        _make_custom_envelope("res-iso-a", "env-iso-a")
        client.post("/v1/dep/resources", json=_make_custom_envelope("res-iso-a", "env-iso-a"), headers={"X-Notary-Org": _ORG_A})
        client.post("/v1/dep/resources", json=_make_custom_envelope("res-iso-b", "env-iso-b"), headers={"X-Notary-Org": _ORG_B})

        resp_a = client.get("/v1/discovery/sources", headers={"X-Notary-Org": _ORG_A})
        ids_a = [r["resource_id"] for r in resp_a.json()]
        assert "res-iso-a" in ids_a
        assert "res-iso-b" not in ids_a

        resp_b = client.get("/v1/discovery/sources", headers={"X-Notary-Org": _ORG_B})
        ids_b = [r["resource_id"] for r in resp_b.json()]
        assert "res-iso-b" in ids_b
        assert "res-iso-a" not in ids_b

    def test_provider_org_isolation(self) -> None:
        body = {"provider_id": "prov-iso-alice", "name": "Alice", "provider_type": "sdk"}
        client.post("/v1/discovery/providers", json=body, headers={"X-Notary-Org": _ORG_A})

        resp = client.get(
            "/v1/discovery/providers/prov-iso-alice",
            headers={"X-Notary-Org": _ORG_B},
        )
        assert resp.status_code == 404

        resp = client.get(
            "/v1/discovery/providers/prov-iso-alice",
            headers={"X-Notary-Org": _ORG_A},
        )
        assert resp.status_code == 200
        assert resp.json()["provider_id"] == "prov-iso-alice"

    def test_same_provider_id_in_different_orgs(self) -> None:
        body = {"provider_id": "prov-shared", "name": "Shared Name", "provider_type": "sdk"}
        resp_a = client.post("/v1/discovery/providers", json=body, headers={"X-Notary-Org": _ORG_A})
        assert resp_a.status_code == 200

        resp_b = client.post("/v1/discovery/providers", json=body, headers={"X-Notary-Org": _ORG_B})
        assert resp_b.status_code == 200

        resp_a_get = client.get("/v1/discovery/providers/prov-shared", headers={"X-Notary-Org": _ORG_A})
        assert resp_a_get.status_code == 200
        assert resp_a_get.json()["name"] == "Shared Name"
