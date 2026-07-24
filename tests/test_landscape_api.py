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
    AdvisorySuggestion,
    ContextBinding,
    ContextConflict,
    DecisionEvidenceRecord,
    DecisionEvidenceResource,
    LinkAssertion,
)
from notary_platform.discovery.sources import SourceConnection
from notary_platform.storage import StorageBackend, get_storage, reset_storage
from notary_platform.sweep.models import (
    AssuranceCandidate,
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
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-1",
            org_id=ORG,
            environment_id="env-prod",
            decision_identity="lending/underwriting",
            identity_method="exact_id",
        )
    )
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-2",
            org_id=ORG,
            environment_id="env-prod",
            decision_identity="lending/credit-check",
            identity_method="exact_id",
        )
    )

    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "decision_families" in body
    identities = {f["identity"] for f in body["decision_families"]}
    assert "lending/underwriting" in identities
    assert "lending/credit-check" in identities


def test_landscape_decision_families_have_evidence_levels() -> None:
    s = get_storage()
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-3",
            org_id=ORG,
            decision_identity="fraud/detection",
            evidence_level="E2",
        )
    )
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    families = {f["identity"]: f for f in body["decision_families"]}
    assert families.get("fraud/detection", {}).get("evidence_level") in ("E2", None)


# ── Connected sources ──


def test_landscape_includes_sources() -> None:
    s = get_storage()
    s.create_resource(
        DecisionEvidenceResource(
            resource_id="res-1",
            org_id=ORG,
            envelope_id="env-1",
            resource_type="decision_log",
            provider_id="prov-1",
            digest_algorithm="sha256",
            digest_value="abc",
            payload_ref="ref-1",
        )
    )
    s.create_resource(
        DecisionEvidenceResource(
            resource_id="res-2",
            org_id=ORG,
            envelope_id="env-2",
            resource_type="audit_trail",
            provider_id="prov-1",
            digest_algorithm="sha256",
            digest_value="def",
            payload_ref="ref-2",
        )
    )

    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "sources" in body
    assert len(body["sources"]) >= 2


# ── Context/policy coverage ──


def test_landscape_includes_context_coverage() -> None:
    s = get_storage()
    s.create_context_binding(
        ContextBinding(
            id="cb-1",
            org_id=ORG,
            environment_id="env-prod",
            subject_scope="decision_family",
            subject_selector="lending/underwriting",
            binding_type="governed_by_policy",
            artifact_ref="pol-1",
        )
    )
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "context_coverage" in body
    assert len(body["context_coverage"]) >= 1


# ── Relationship status ──


def test_landscape_includes_relationship_status() -> None:
    s = get_storage()
    s.create_link_assertion(
        LinkAssertion(
            id="la-1",
            org_id=ORG,
            source_resource_id="res-1",
            target_resource_id="res-2",
            relationship="governed_by_policy",
            basis="exact_id",
            status="inferred",
        )
    )
    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body = resp.json()
    assert "relationships" in body
    assert len(body["relationships"]) >= 1
    assert body["relationships"][0]["status"] in ("confirmed", "inferred", "ambiguous", "missing", "conflicted")


# ── Evaluator availability ──


def test_landscape_includes_evaluator_availability() -> None:
    s = get_storage()
    s.create_evaluator_contract(
        EvaluatorContractRecord(
            id="eval-1",
            org_id=ORG,
            name="outcome-check",
            method_class="deterministic",
            trust_class="authoritative",
        )
    )
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
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-a",
            org_id="org-a",
            decision_identity="loan/approval",
        )
    )
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-b",
            org_id="org-b",
            decision_identity="fraud/scan",
        )
    )

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
    s.create_sweep_run(
        SweepRun(
            id="sr-1",
            org_id=ORG,
            status="completed",
            record_count=100,
            evaluator_count=5,
            executed_count=5,
            candidate_count=2,
        )
    )
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


# ── Environment scoping (WP-100 review fix) ──


def test_landscape_is_environment_scoped() -> None:
    s = get_storage()
    # env-prod data
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-prod",
            org_id=ORG,
            environment_id="env-prod",
            decision_identity="lending/approval",
            source_resource_ids=["res-prod-1"],
        )
    )
    s.create_resource(
        DecisionEvidenceResource(
            resource_id="res-prod-1",
            org_id=ORG,
            environment_id="env-prod",
            resource_type="decision_log",
            envelope_id="e1",
            provider_id="p1",
            digest_algorithm="sha256",
            digest_value="a",
            payload_ref="r1",
        )
    )
    s.create_resource(
        DecisionEvidenceResource(
            resource_id="res-prod-2",
            org_id=ORG,
            environment_id="env-prod",
            resource_type="audit_trail",
            envelope_id="e2",
            provider_id="p1",
            digest_algorithm="sha256",
            digest_value="b",
            payload_ref="r2",
        )
    )
    s.create_context_binding(
        ContextBinding(
            id="cb-prod",
            org_id=ORG,
            environment_id="env-prod",
            subject_scope="decision_family",
            subject_selector="lending/approval",
            binding_type="governed_by_policy",
            artifact_ref="pol-1",
        )
    )
    s.create_link_assertion(
        LinkAssertion(
            id="la-prod",
            org_id=ORG,
            source_resource_id="res-prod-1",
            target_resource_id="res-prod-2",
            relationship="governed_by_policy",
            basis="exact_id",
            status="confirmed",
        )
    )
    s.create_sweep_run(
        SweepRun(
            id="sr-prod",
            org_id=ORG,
            environment_id="env-prod",
            status="completed",
            record_count=2,
            evaluator_count=1,
            executed_count=2,
            candidate_count=1,
        )
    )
    s.create_assurance_candidate(
        AssuranceCandidate(
            id="ac-prod",
            org_id=ORG,
            environment_id="env-prod",
            sweep_run_id="sr-prod",
            lifecycle_state="needs_context",
        )
    )
    s.create_context_conflict(
        ContextConflict(
            id="cf-prod",
            org_id=ORG,
            der_id="der-prod",
            field_or_binding="amount",
            binding_a_id="pol-a",
            binding_b_id="pol-b",
        )
    )
    # env-staging data
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-stag",
            org_id=ORG,
            environment_id="env-staging",
            decision_identity="fraud/scan",
            source_resource_ids=["res-stag-1"],
        )
    )
    s.create_resource(
        DecisionEvidenceResource(
            resource_id="res-stag-1",
            org_id=ORG,
            environment_id="env-staging",
            resource_type="dashboard",
            envelope_id="e3",
            provider_id="p2",
            digest_algorithm="sha256",
            digest_value="c",
            payload_ref="r3",
        )
    )
    s.create_context_binding(
        ContextBinding(
            id="cb-stag",
            org_id=ORG,
            environment_id="env-staging",
            subject_scope="decision_family",
            subject_selector="fraud/scan",
            binding_type="governed_by_policy",
            artifact_ref="pol-2",
        )
    )
    s.create_link_assertion(
        LinkAssertion(
            id="la-stag",
            org_id=ORG,
            source_resource_id="res-stag-1",
            target_resource_id="res-stag-1",
            relationship="self_ref",
            basis="exact_id",
            status="inferred",
        )
    )
    s.create_sweep_run(
        SweepRun(
            id="sr-stag",
            org_id=ORG,
            environment_id="env-staging",
            status="running",
            record_count=1,
            evaluator_count=1,
            executed_count=0,
            candidate_count=0,
        )
    )
    s.create_assurance_candidate(
        AssuranceCandidate(
            id="ac-stag",
            org_id=ORG,
            environment_id="env-staging",
            sweep_run_id="sr-stag",
            lifecycle_state="draft",
        )
    )
    s.create_context_conflict(
        ContextConflict(
            id="cf-stag",
            org_id=ORG,
            der_id="der-stag",
            field_or_binding="threshold",
            binding_a_id="pol-c",
            binding_b_id="pol-d",
        )
    )
    # org-wide data (no environment_id)
    s.create_source_connection(
        SourceConnection(
            id="sc-1",
            org_id=ORG,
            name="Shared DB",
            source_type="dep",
            status="connected",
        )
    )
    s.create_evaluator_contract(
        EvaluatorContractRecord(
            id="eval-1",
            org_id=ORG,
            name="outcome-check",
            method_class="deterministic",
            trust_class="authoritative",
        )
    )
    s.create_advisory_suggestion(
        AdvisorySuggestion(
            id="as-1",
            org_id=ORG,
            suggestion_type="policy_candidate",
            content={"note": "review"},
            status="inferred",
        )
    )

    resp = client.get("/v1/discovery/landscape", headers=ORG_HEADERS)
    body_all = resp.json()
    assert len(body_all["decision_families"]) == 2
    assert len(body_all["sources"]) == 3

    # ── env-prod scope ──
    resp_prod = client.get("/v1/discovery/landscape?environment_id=env-prod", headers=ORG_HEADERS)
    body = resp_prod.json()

    assert body["org_id"] == ORG
    # decision_families only env-prod
    assert {f["identity"] for f in body["decision_families"]} == {"lending/approval"}
    # sources only env-prod
    assert len(body["sources"]) == 2
    assert {s["id"] for s in body["sources"]} == {"res-prod-1", "res-prod-2"}
    # source_profiles includes all (org-wide)
    assert len(body["source_profiles"]) == 1
    assert body["source_profiles"][0]["id"] == "sc-1"
    # context_coverage only env-prod
    assert len(body["context_coverage"]) == 1
    assert body["context_coverage"][0]["id"] == "cb-prod"
    # relationships only env-prod links
    assert len(body["relationships"]) == 1
    assert body["relationships"][0]["id"] == "la-prod"
    # evaluators includes all (org-wide)
    assert len(body["evaluators"]) == 1
    # required_corrections includes unresolved env-prod conflict but not no-sources/no-evaluators
    assert "no_sources_connected" not in body["required_corrections"]
    assert "no_evaluators_registered" not in body["required_corrections"]
    assert "unresolved_conflict:cf-prod" in body["required_corrections"]
    # optional_enrichment does not include no-der or no-binding (env-prod has both)
    assert "no_decision_records_built" not in body["optional_enrichment"]
    assert "no_context_bindings_configured" not in body["optional_enrichment"]
    # evidence_gaps only env-prod resource not covered by env-prod DER
    gap_resource_ids = [g["resource_id"] for g in body["evidence_gaps"] if g["gap_type"] == "not_covered_by_any_der"]
    assert "res-prod-2" in gap_resource_ids  # not in der.source_resource_ids
    assert "res-prod-1" not in gap_resource_ids  # covered by der-prod
    assert "res-stag-1" not in gap_resource_ids  # belongs to staging
    gap_conflict_ids = [g.get("conflict_id", "") for g in body["evidence_gaps"] if g["gap_type"] == "context_conflict"]
    assert "cf-prod" in gap_conflict_ids
    assert "cf-stag" not in gap_conflict_ids
    # sweep_summary only env-prod runs
    assert body["sweep_summary"]["total_runs"] == 1
    assert body["sweep_summary"]["completed_runs"] == 1
    assert body["sweep_summary"]["active_runs"] == 0
    assert body["sweep_summary"]["total_candidates"] == 1
    assert body["sweep_summary"]["active_candidates"] == 1
    # next_actions does not include env-b candidates
    next_action_labels = {a["action"] for a in body["next_actions"]}
    assert "connect_source" not in next_action_labels
    assert "ingest_resources" not in next_action_labels
    # advisory_signals includes all (org-wide)
    assert len(body["advisory_signals"]) == 1
    assert body["advisory_signals"][0]["id"] == "as-1"

    # ── env-staging scope ──
    resp_stag = client.get("/v1/discovery/landscape?environment_id=env-staging", headers=ORG_HEADERS)
    body = resp_stag.json()

    assert {f["identity"] for f in body["decision_families"]} == {"fraud/scan"}
    assert len(body["sources"]) == 1
    assert body["sources"][0]["id"] == "res-stag-1"
    assert len(body["source_profiles"]) == 1  # org-wide
    assert len(body["context_coverage"]) == 1
    assert body["context_coverage"][0]["id"] == "cb-stag"
    assert len(body["relationships"]) == 1
    assert body["relationships"][0]["id"] == "la-stag"
    assert len(body["evaluators"]) == 1  # org-wide
    assert "unresolved_conflict:cf-stag" in body["required_corrections"]
    assert "unresolved_conflict:cf-prod" not in body["required_corrections"]
    assert body["sweep_summary"]["total_runs"] == 1
    assert body["sweep_summary"]["completed_runs"] == 0
    assert body["sweep_summary"]["active_candidates"] == 0  # staging candidate is draft
    gap_stag_resource_ids = {g["resource_id"] for g in body["evidence_gaps"] if g["gap_type"] == "not_covered_by_any_der"}
    assert "res-stag-1" not in gap_stag_resource_ids  # covered by der-stag
    assert "res-prod-1" not in gap_stag_resource_ids  # belongs to prod
    assert "res-prod-2" not in gap_stag_resource_ids
    assert len(body["advisory_signals"]) == 1  # org-wide


def test_landscape_unknown_environment_returns_empty_environment_data() -> None:
    s = get_storage()
    s.create_decision_evidence_record(
        DecisionEvidenceRecord(
            id="der-1",
            org_id=ORG,
            environment_id="env-prod",
            decision_identity="lending/approval",
        )
    )
    s.create_source_connection(
        SourceConnection(
            id="sc-1",
            org_id=ORG,
            name="Shared DB",
            source_type="dep",
            status="connected",
        )
    )
    s.create_evaluator_contract(
        EvaluatorContractRecord(
            id="eval-1",
            org_id=ORG,
            name="outcome-check",
            method_class="deterministic",
            trust_class="authoritative",
        )
    )
    resp = client.get("/v1/discovery/landscape?environment_id=env-nonexistent", headers=ORG_HEADERS)
    body = resp.json()
    assert body["decision_families"] == []
    assert body["sources"] == []
    assert body["context_coverage"] == []
    assert body["relationships"] == []
    assert body["evidence_gaps"] == []
    assert body["sweep_summary"]["total_runs"] == 0
    assert body["sweep_summary"]["total_candidates"] == 0
    # org-wide sections still present
    assert len(body["source_profiles"]) == 1
    assert len(body["evaluators"]) == 1
