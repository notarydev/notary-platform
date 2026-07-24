"""WP-080: Assurance Candidate assembly, review, suppression, and delegation tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.storage import StorageBackend, get_storage, reset_storage
from notary_platform.sweep.candidates import CandidateAssembler, CandidateReviewService
from notary_platform.sweep.evaluators.base import (
    FrozenDecisionEvidenceRecord,
    ResolvedContext,
)
from notary_platform.sweep.models import (
    AssessmentRecord,
    AssuranceCandidate,
    PromotionDelegation,
    ReviewDecision,
    SuppressionRule,
)


@pytest.fixture(autouse=True)
def _reset() -> StorageBackend:
    reset_storage()
    return get_storage()


client = TestClient(app)


# ── Candidate Assembler ──


class TestCandidateAssembler:
    def test_assembles_candidate_from_assessment(self) -> None:
        s = get_storage()
        record = FrozenDecisionEvidenceRecord(
            id="der-1", org_id="test-org", decision_identity="res-1",
            identity_method="exact_id", source_resource_ids=("res-1",),
            context_binding_ids=("cb-1",), link_assertion_ids=(),
            resolution_trace_id="rt-1", enriched=False, version=1,
            created_at="2026-07-01T12:00:00Z",
        )
        context = ResolvedContext(
            binding_ids=("cb-1",), included_artifacts=("res-1",),
            excluded_artifacts=(), superseded_bindings=(),
            conflicted_bindings=(), missing_artifacts=(),
            stale_artifacts=(), redacted_artifacts=(),
            reasons={"authoritative_context": True},
        )
        assessment = AssessmentRecord(
            id="ar-1", org_id="test-org", run_id="sr-1",
            evaluator_id="eval-001", der_id="der-1",
            finding_type="expected_outcome_mismatch", status="assessed",
            summary="outcome mismatch", details={"actual_outcome": "denied", "expected_outcome": "approved"},
        )
        assembler = CandidateAssembler(s)
        candidates = assembler.assemble([assessment], record, context, "sr-1", "env-prod")
        assert len(candidates) == 1
        assert candidates[0].candidate_type == "expected_outcome_mismatch"
        assert candidates[0].evidence_level == "E3"
        assert candidates[0].lifecycle_state == "reviewable"

    def test_skips_assessment_without_finding(self) -> None:
        s = get_storage()
        record = FrozenDecisionEvidenceRecord(
            id="der-2", org_id="test-org", decision_identity="res-2",
            identity_method="exact_id", source_resource_ids=(),
            context_binding_ids=(), link_assertion_ids=(),
            resolution_trace_id="", enriched=False, version=1,
            created_at="2026-07-01T12:00:00Z",
        )
        context = ResolvedContext(
            binding_ids=(), included_artifacts=(), excluded_artifacts=(),
            superseded_bindings=(), conflicted_bindings=(),
            missing_artifacts=(), stale_artifacts=(), redacted_artifacts=(),
        )
        assessment = AssessmentRecord(
            id="ar-ok", org_id="test-org", run_id="sr-1",
            evaluator_id="eval-001", der_id="der-2",
            finding_type="", status="assessed",
            summary="all good", details={"status": "matched"},
        )
        assembler = CandidateAssembler(s)
        candidates = assembler.assemble([assessment], record, context, "sr-1")
        assert len(candidates) == 0

    def test_skips_non_assessed_status(self) -> None:
        s = get_storage()
        record = FrozenDecisionEvidenceRecord(
            id="der-3", org_id="test-org", decision_identity="res-3",
            identity_method="exact_id", source_resource_ids=(),
            context_binding_ids=(), link_assertion_ids=(),
            resolution_trace_id="", enriched=False, version=1,
            created_at="2026-07-01T12:00:00Z",
        )
        context = ResolvedContext(
            binding_ids=(), included_artifacts=(), excluded_artifacts=(),
            superseded_bindings=(), conflicted_bindings=(),
            missing_artifacts=(), stale_artifacts=(), redacted_artifacts=(),
        )
        assessment = AssessmentRecord(
            id="ar-skip", org_id="test-org", run_id="sr-1",
            evaluator_id="eval-001", der_id="der-3",
            finding_type="missing_evidence", status="skipped",
            summary="skipped", details={},
        )
        assembler = CandidateAssembler(s)
        candidates = assembler.assemble([assessment], record, context, "sr-1")
        assert len(candidates) == 0


# ── Candidate Review Service ──


class TestCandidateReviewService:
    def test_record_review_approves(self) -> None:
        s = get_storage()
        candidate = s.create_assurance_candidate(AssuranceCandidate(
            org_id="test-org", candidate_type="missing_evidence",
            lifecycle_state="reviewable",
        ))
        svc = CandidateReviewService(s)
        decision = ReviewDecision(
            candidate_id=candidate.id, org_id="test-org",
            actor="reviewer-1", role="auditor",
            decision="approve_incident", basis="confirmed finding",
        )
        created = svc.record_review(candidate.id, decision)
        assert created is not None
        assert created.decision == "approve_incident"
        updated = s.get_assurance_candidate(candidate.id)
        assert updated is not None
        assert updated.lifecycle_state == "approved_incident"

    def test_record_review_dismisses(self) -> None:
        s = get_storage()
        candidate = s.create_assurance_candidate(AssuranceCandidate(
            org_id="test-org", candidate_type="replayability_failure",
            lifecycle_state="reviewable",
        ))
        svc = CandidateReviewService(s)
        decision = ReviewDecision(
            candidate_id=candidate.id, org_id="test-org",
            actor="reviewer-1", role="auditor",
            decision="dismiss", basis="not a real issue",
        )
        svc.record_review(candidate.id, decision)
        updated = s.get_assurance_candidate(candidate.id)
        assert updated is not None
        assert updated.lifecycle_state == "dismissed"

    def test_record_review_wrong_org(self) -> None:
        s = get_storage()
        candidate = s.create_assurance_candidate(AssuranceCandidate(
            org_id="test-org", candidate_type="missing_evidence",
        ))
        svc = CandidateReviewService(s)
        decision = ReviewDecision(
            candidate_id=candidate.id, org_id="other-org",
            actor="hacker", role="none",
            decision="approve_incident", basis="",
        )
        result = svc.record_review(candidate.id, decision)
        assert result is None

    def test_get_reviews(self) -> None:
        s = get_storage()
        candidate = s.create_assurance_candidate(AssuranceCandidate(org_id="test-org"))
        svc = CandidateReviewService(s)
        d1 = ReviewDecision(candidate_id=candidate.id, org_id="test-org", actor="a", role="r", decision="dismiss", basis="b1")
        d2 = ReviewDecision(candidate_id=candidate.id, org_id="test-org", actor="b", role="r", decision="approve_incident", basis="b2")
        s.create_review_decision(d1)
        s.create_review_decision(d2)
        reviews = svc.get_reviews(candidate.id)
        assert len(reviews) == 2

    def test_create_suppression(self) -> None:
        s = get_storage()
        svc = CandidateReviewService(s)
        rule = SuppressionRule(org_id="test-org", scope="candidate_type", scope_value="missing_evidence", reason="known false positive", created_by="admin")
        created = svc.create_suppression(rule)
        assert created.id.startswith("sr-")

    def test_list_suppressions(self) -> None:
        s = get_storage()
        svc = CandidateReviewService(s)
        svc.create_suppression(SuppressionRule(org_id="test-org", scope="der_id", scope_value="der-1", reason="r1", created_by="admin"))
        svc.create_suppression(SuppressionRule(org_id="test-org", scope="der_id", scope_value="der-2", reason="r2", created_by="admin"))
        rules = svc.list_suppressions("test-org")
        assert len(rules) == 2

    def test_create_delegation(self) -> None:
        s = get_storage()
        svc = CandidateReviewService(s)
        d = PromotionDelegation(
            org_id="test-org", name="auto-approve", rule_type="deterministic",
            conditions={"evidence_level": "E3"}, scope="expected_outcome_mismatch",
        )
        created = svc.create_delegation(d)
        assert created.id.startswith("pd-")

    def test_list_delegations(self) -> None:
        s = get_storage()
        svc = CandidateReviewService(s)
        svc.create_delegation(PromotionDelegation(org_id="test-org", name="d1", rule_type="deterministic"))
        svc.create_delegation(PromotionDelegation(org_id="test-org", name="d2", rule_type="deterministic"))
        delegations = svc.list_delegations("test-org")
        assert len(delegations) == 2

    def test_check_delegation_matches(self) -> None:
        s = get_storage()
        svc = CandidateReviewService(s)
        svc.create_delegation(PromotionDelegation(
            org_id="test-org", name="auto-approve", rule_type="deterministic",
            conditions={"evidence_level": "E3"}, scope="expected_outcome_mismatch",
        ))
        candidate = AssuranceCandidate(org_id="test-org", candidate_type="expected_outcome_mismatch", evidence_level="E3")
        match = svc.check_delegation(candidate, "test-org")
        assert match is not None
        assert match.name == "auto-approve"

    def test_check_delegation_no_match(self) -> None:
        s = get_storage()
        svc = CandidateReviewService(s)
        svc.create_delegation(PromotionDelegation(
            org_id="test-org", name="strict", rule_type="deterministic",
            conditions={"evidence_level": "E4"}, scope="expected_outcome_mismatch",
        ))
        candidate = AssuranceCandidate(org_id="test-org", candidate_type="missing_evidence", evidence_level="E3")
        match = svc.check_delegation(candidate, "test-org")
        assert match is None


# ── Router integration tests ──


class TestCandidatesRouter:
    def test_list_candidates_empty(self) -> None:
        resp = client.get("/v1/discovery/candidates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_candidate_not_found(self) -> None:
        resp = client.get("/v1/discovery/candidates/ac-nonexistent")
        assert resp.status_code == 404

    def test_create_review(self) -> None:
        s = get_storage()
        c = s.create_assurance_candidate(AssuranceCandidate(org_id="demo-org", candidate_type="missing_evidence", lifecycle_state="reviewable"))
        resp = client.post(f"/v1/discovery/candidates/{c.id}/reviews", json={
            "actor": "reviewer-1",
            "role": "auditor",
            "decision": "approve_incident",
            "basis": "confirmed",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "approve_incident"

    def test_create_review_404(self) -> None:
        resp = client.post("/v1/discovery/candidates/ac-nonexistent/reviews", json={
            "actor": "a", "role": "r", "decision": "dismiss",
        })
        assert resp.status_code == 404

    def test_list_reviews(self) -> None:
        s = get_storage()
        c = s.create_assurance_candidate(AssuranceCandidate(org_id="demo-org"))
        s.create_review_decision(ReviewDecision(candidate_id=c.id, org_id="demo-org", actor="a", role="r", decision="dismiss", basis="b1"))
        s.create_review_decision(ReviewDecision(candidate_id=c.id, org_id="demo-org", actor="b", role="r", decision="approve_incident", basis="b2"))
        resp = client.get(f"/v1/discovery/candidates/{c.id}/reviews")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_create_suppression_via_router(self) -> None:
        resp = client.post("/v1/discovery/suppressions", json={
            "scope": "candidate_type",
            "scope_value": "missing_evidence",
            "reason": "known false positive",
            "created_by": "admin",
        })
        assert resp.status_code == 200
        assert resp.json()["scope"] == "candidate_type"

    def test_list_suppressions_via_router(self) -> None:
        client.post("/v1/discovery/suppressions", json={"scope": "der_id", "scope_value": "der-1", "reason": "r1", "created_by": "admin"})
        client.post("/v1/discovery/suppressions", json={"scope": "der_id", "scope_value": "der-2", "reason": "r2", "created_by": "admin"})
        resp = client.get("/v1/discovery/suppressions")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_create_delegation_via_router(self) -> None:
        resp = client.post("/v1/discovery/promotion-delegations", json={
            "name": "auto-approve",
            "rule_type": "deterministic",
            "conditions": {"evidence_level": "E3"},
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "auto-approve"

    def test_list_delegations_via_router(self) -> None:
        client.post("/v1/discovery/promotion-delegations", json={"name": "d1", "rule_type": "deterministic"})
        client.post("/v1/discovery/promotion-delegations", json={"name": "d2", "rule_type": "deterministic"})
        resp = client.get("/v1/discovery/promotion-delegations")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
