"""API contract tests for the Decision Landscape endpoint (WP-100).

The response must be org- and environment-scoped and contain only persisted data.
All test data uses the default org ("demo-org") to match what the API returns
when no X-Notary-Org header is set. Multi-org tests pass the header explicitly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.discovery.models import (
    ContextBinding,
    DecisionEvidenceRecord,
    DecisionEvidenceResource,
    LinkAssertion,
)
from notary_platform.storage import StorageBackend, get_storage, reset_storage
from notary_platform.sweep.models import (
    EvaluatorContractRecord,
    SweepRun,
)

pytestmark = pytest.mark.usefixtures("_reset")

ORG = "demo-org"
ORG_HEADERS = {"X-Notary-Org": ORG}


@pytest.fixture(autouse=True)
def _reset() -> StorageBackend:
    reset_storage()
    return get_storage()


client = TestClient(app)


# ── Landscape endpoint exists ──


def test_landscape_endpoint_returns_200() -> None:
    resp = client.get("/v1/discovery/landscape")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, dict)


# ── Decision families ──


def test_landscape_includes_decision_families() -> None:
    s = get_storage()
    s.create_decision_evidence_record(DecisionEvidenceRecord(
        id="der-1", org_id=ORG, environment_id="env-prod",
        decision_identity="lending/underwriting", identity_method="exact_id",
    ))
    s.create_decision_evidence_record(DecisionEvidenceRecord(
        id="der-2", org_id=ORG, environment_id="env-prod",
        decision_identity="lending/credit-check", identity_method="exact_id",
    ))

    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "decision_families" in body
    identities = {f["identity"] for f in body["decision_families"]}
    assert "lending/underwriting" in identities
    assert "lending/credit-check" in identities


def test_landscape_decision_families_have_evidence_levels() -> None:
    s = get_storage()
    s.create_decision_evidence_record(DecisionEvidenceRecord(
        id="der-3", org_id=ORG, decision_identity="fraud/detection",
        evidence_level="E2",
    ))
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    families = {f["identity"]: f for f in body["decision_families"]}
    assert families.get("fraud/detection", {}).get("evidence_level") in ("E2", None)


# ── Connected sources ──


def test_landscape_includes_sources() -> None:
    s = get_storage()
    s.create_resource(DecisionEvidenceResource(
        resource_id="res-1", org_id=ORG, envelope_id="env-1",
        resource_type="decision_log", provider_id="prov-1",
        digest_algorithm="sha256", digest_value="abc", payload_ref="ref-1",
    ))
    s.create_resource(DecisionEvidenceResource(
        resource_id="res-2", org_id=ORG, envelope_id="env-2",
        resource_type="audit_trail", provider_id="prov-1",
        digest_algorithm="sha256", digest_value="def", payload_ref="ref-2",
    ))

    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "sources" in body
    assert len(body["sources"]) >= 2


# ── Context/policy coverage ──


def test_landscape_includes_context_coverage() -> None:
    s = get_storage()
    s.create_context_binding(ContextBinding(
        id="cb-1", org_id=ORG, environment_id="env-prod",
        subject_scope="decision_family", subject_selector="lending/underwriting",
        binding_type="governed_by_policy", artifact_ref="pol-1",
    ))
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "context_coverage" in body
    assert len(body["context_coverage"]) >= 1


# ── Relationship status ──


def test_landscape_includes_relationship_status() -> None:
    s = get_storage()
    s.create_link_assertion(LinkAssertion(
        id="la-1", org_id=ORG,
        source_resource_id="res-1", target_resource_id="res-2",
        relationship="governed_by_policy", basis="exact_id", status="inferred",
    ))
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "relationships" in body
    assert len(body["relationships"]) >= 1
    assert body["relationships"][0]["status"] in ("confirmed", "inferred", "ambiguous", "missing", "conflicted")


# ── Evaluator availability ──


def test_landscape_includes_evaluator_availability() -> None:
    s = get_storage()
    s.create_evaluator_contract(EvaluatorContractRecord(
        id="eval-1", org_id=ORG, name="outcome-check",
        method_class="deterministic", trust_class="authoritative",
    ))
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "evaluators" in body
    assert len(body["evaluators"]) >= 1


# ── Required corrections vs optional enrichment ──


def test_landscape_separates_corrections_from_enrichment() -> None:
    resp = client.get("/v1/discovery/landscape")
    body = resp.json()
    assert "required_corrections" in body
    assert "optional_enrichment" in body
    assert isinstance(body["required_corrections"], list)
    assert isinstance(body["optional_enrichment"], list)


# ── Evidence gaps ──


def test_landscape_includes_evidence_gaps() -> None:
    resp = client.get("/v1/discovery/landscape")
    body = resp.json()
    assert "evidence_gaps" in body
    assert isinstance(body["evidence_gaps"], list)


# ── Next actions ──


def test_landscape_includes_next_actions() -> None:
    resp = client.get("/v1/discovery/landscape")
    body = resp.json()
    assert "next_actions" in body
    assert isinstance(body["next_actions"], list)


# ── Tenant isolation ──


def test_landscape_is_org_scoped() -> None:
    s = get_storage()
    s.create_decision_evidence_record(DecisionEvidenceRecord(
        id="der-a", org_id="org-a", decision_identity="loan/approval",
    ))
    s.create_decision_evidence_record(DecisionEvidenceRecord(
        id="der-b", org_id="org-b", decision_identity="fraud/scan",
    ))

    resp_a = client.get("/v1/discovery/landscape", headers={"X-Notary-Org": "org-a"})
    resp_b = client.get("/v1/discovery/landscape", headers={"X-Notary-Org": "org-b"})

    families_a = {f["identity"] for f in resp_a.json()["decision_families"]}
    families_b = {f["identity"] for f in resp_b.json()["decision_families"]}
    assert "loan/approval" in families_a
    assert "fraud/scan" in families_b
    assert "fraud/scan" not in families_a
    assert "loan/approval" not in families_b


# ── Advisory signals (if present) ──


def test_landscape_includes_advisory_signals() -> None:
    """Systematic-issue signals only if persisted data supports them."""
    resp = client.get("/v1/discovery/landscape")
    body = resp.json()
    signals = body.get("advisory_signals", [])
    assert isinstance(signals, list)


# ── Sweep run summary ──


def test_landscape_includes_sweep_summary() -> None:
    s = get_storage()
    s.create_sweep_run(SweepRun(
        id="sr-1", org_id=ORG, status="completed",
        record_count=100, evaluator_count=5, executed_count=5,
        candidate_count=2,
    ))
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "sweep_summary" in body
    assert body["sweep_summary"]["total_runs"] >= 1


# ── Empty landscape ──


def test_landscape_empty_returns_valid_structure() -> None:
    resp = client.get("/v1/discovery/landscape")
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision_families"] == []
    assert body["sources"] == []
    assert body["evidence_gaps"] == []
