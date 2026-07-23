"""WP-050: Decision identity resolver tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.storage import get_storage, reset_storage


@pytest.fixture(autouse=True)
def _reset():
    reset_storage()
    return get_storage()


client = TestClient(app)


class TestBasicDer:
    def test_create_der_without_prior_identity(self) -> None:
        der = client.post("/v1/discovery/records", json={
            "resource_ids": ["res-fresh-123"],
            "decision_time": "2026-07-01T12:00:00Z",
        })
        assert der.status_code == 200
        data = der.json()
        assert data["decision_identity"] == "res-fresh-123"
        assert data["identity_method"] == "inferred"

    def test_each_create_returns_new_der(self) -> None:
        r1 = client.post("/v1/discovery/records", json={
            "resource_ids": ["res-same-id"],
        })
        r2 = client.post("/v1/discovery/records", json={
            "resource_ids": ["res-same-id"],
        })
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] != r2.json()["id"]

    def test_exact_id_resolved_when_der_exists(self) -> None:
        client.post("/v1/discovery/records", json={
            "resource_ids": ["res-known"],
        })
        der = client.post("/v1/discovery/records", json={
            "resource_ids": ["res-known"],
        })
        assert der.status_code == 200
        data = der.json()
        assert data["decision_identity"] == "res-known"
        assert data["identity_method"] == "exact_id"


class TestLinkAssertions:
    def test_create_link_assertion(self) -> None:
        resp = client.post("/v1/discovery/link-assertions", json={
            "source_resource_id": "res-1",
            "target_resource_id": "res-2",
            "relationship": "same_decision",
            "basis": "exact_id",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "inferred"

    def test_confirm_link_assertion(self) -> None:
        created = client.post("/v1/discovery/link-assertions", json={
            "source_resource_id": "res-a",
            "target_resource_id": "res-b",
            "relationship": "same_decision",
        }).json()
        resp = client.post(f"/v1/discovery/link-assertions/{created['id']}/confirm")
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
        assert resp.json()["confirmed_at"] != ""

    def test_reject_link_assertion(self) -> None:
        created = client.post("/v1/discovery/link-assertions", json={
            "source_resource_id": "res-x",
            "target_resource_id": "res-y",
            "relationship": "same_decision",
        }).json()
        resp = client.post(f"/v1/discovery/link-assertions/{created['id']}/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_confirm_nonexistent_returns_404(self) -> None:
        resp = client.post("/v1/discovery/link-assertions/nonexistent/confirm")
        assert resp.status_code == 404

    def test_reject_nonexistent_returns_404(self) -> None:
        resp = client.post("/v1/discovery/link-assertions/nonexistent/reject")
        assert resp.status_code == 404


class TestDecisionEvidenceRecords:
    def test_create_and_get_der(self) -> None:
        created = client.post("/v1/discovery/records", json={
            "resource_ids": ["res-123"],
        }).json()
        got = client.get(f"/v1/discovery/records/{created['id']}")
        assert got.status_code == 200
        assert got.json()["id"] == created["id"]

    def test_list_ders(self) -> None:
        client.post("/v1/discovery/records", json={"resource_ids": ["res-a"]})
        client.post("/v1/discovery/records", json={"resource_ids": ["res-b"]})
        resp = client.get("/v1/discovery/records")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_nonexistent_der(self) -> None:
        resp = client.get("/v1/discovery/records/nonexistent")
        assert resp.status_code == 404

    def test_der_includes_context_bindings_on_resolution(self) -> None:
        client.post("/v1/discovery/context-bindings", json={
            "subject_scope": "res-456",
            "subject_selector": "",
            "binding_type": "governed_by_policy",
            "artifact_ref": "ref://policy/1",
            "effective_from": "2026-01-01T00:00:00Z",
            "authority": "customer_confirmed",
        })
        created = client.post("/v1/discovery/records", json={
            "resource_ids": ["res-456"],
            "decision_time": "2026-06-15T12:00:00Z",
        }).json()
        assert len(created["context_binding_ids"]) > 0

    def test_resolution_trace_returns_bindings(self) -> None:
        created = client.post("/v1/discovery/records", json={
            "resource_ids": ["res-trace-test"],
        }).json()
        trace = client.get(f"/v1/discovery/records/{created['id']}/resolution-trace")
        assert trace.status_code == 200
        assert "included_bindings" in trace.json()
        assert "reasons" in trace.json()

    def test_resolution_trace_not_found(self) -> None:
        resp = client.get("/v1/discovery/records/fake/resolution-trace")
        assert resp.status_code == 404


class TestContextBindings:
    def test_create_context_binding(self) -> None:
        resp = client.post("/v1/discovery/context-bindings", json={
            "subject_scope": "lending/underwriting",
            "subject_selector": "underwriting-v2",
            "binding_type": "governed_by_policy",
            "artifact_ref": "ref://policy/underwriting/v2",
            "effective_from": "2026-01-01T00:00:00Z",
            "authority": "customer_confirmed",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["subject_scope"] == "lending/underwriting"
        assert data["effective_from"] != ""

    def test_context_conflict_blocks_evaluator(self) -> None:
        scope = "lending/conflict-test"
        sel = "v1"
        client.post("/v1/discovery/context-bindings", json={
            "subject_scope": scope,
            "subject_selector": sel,
            "binding_type": "governed_by_policy",
            "artifact_ref": "ref://policy/a",
            "effective_from": "2026-01-01T00:00:00Z",
            "authority": "provider_declared",
        })
        client.post("/v1/discovery/context-bindings", json={
            "subject_scope": scope,
            "subject_selector": sel,
            "binding_type": "governed_by_policy",
            "artifact_ref": "ref://policy/b",
            "effective_from": "2026-01-01T00:00:00Z",
            "authority": "provider_declared",
        })
        created = client.post("/v1/discovery/records", json={
            "resource_ids": [f"res-{scope}"],
            "decision_time": "2026-06-15T12:00:00Z",
        }).json()
        der = client.get(f"/v1/discovery/records/{created['id']}").json()
        assert len(der.get("context_binding_ids", [])) == 0


class TestContextConflicts:
    def test_resolve_context_conflict(self) -> None:
        cc = client.post("/v1/discovery/context-conflicts/nonexistent/resolve", json={
            "resolution": "resolved_use_a",
            "resolved_by": "user",
        })
        assert cc.status_code == 404

    def test_resolve_missing_resolution_field(self) -> None:
        resp = client.post("/v1/discovery/context-conflicts/fake/resolve", json={})
        assert resp.status_code == 422

    def test_list_conflicts(self) -> None:
        client.post("/v1/discovery/context-bindings", json={
            "subject_scope": "scope-list-test",
            "subject_selector": "sel",
            "binding_type": "governed_by_policy",
            "artifact_ref": "ref://policy/x",
            "effective_from": "2026-01-01T00:00:00Z",
            "authority": "provider_declared",
        })
        client.post("/v1/discovery/context-bindings", json={
            "subject_scope": "scope-list-test",
            "subject_selector": "sel",
            "binding_type": "governed_by_policy",
            "artifact_ref": "ref://policy/y",
            "effective_from": "2026-01-01T00:00:00Z",
            "authority": "provider_declared",
        })
        client.post("/v1/discovery/records", json={
            "resource_ids": ["res-scope-list-test"],
            "decision_time": "2026-06-15T12:00:00Z",
        })
        suggestions = client.get("/v1/discovery/suggestions?workflow_id=")
        assert suggestions.status_code == 200


class TestAdvisorySuggestions:
    def test_create_suggestion(self) -> None:
        resp = client.post("/v1/discovery/suggestions", json={
            "suggestion_type": "policy_candidate",
            "workflow_id": "wf-lending",
            "basis": "inferred from document",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "inferred"

    def test_list_suggestions(self) -> None:
        client.post("/v1/discovery/suggestions", json={
            "suggestion_type": "policy_candidate",
            "workflow_id": "wf-lending",
        })
        client.post("/v1/discovery/suggestions", json={
            "suggestion_type": "context_source_candidate",
            "workflow_id": "wf-lending",
        })
        resp = client.get("/v1/discovery/suggestions?workflow_id=wf-lending")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_policy_candidates_endpoint(self) -> None:
        client.post("/v1/discovery/suggestions", json={
            "suggestion_type": "policy_candidate",
            "workflow_id": "wf-lending",
        })
        resp = client.get("/v1/discovery/workflows/wf-lending/policy-candidates")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_context_roadmap_endpoint(self) -> None:
        client.post("/v1/discovery/suggestions", json={
            "suggestion_type": "context_source_candidate",
            "workflow_id": "wf-lending",
        })
        resp = client.get("/v1/discovery/workflows/wf-lending/context-roadmap")
        assert resp.status_code == 200
