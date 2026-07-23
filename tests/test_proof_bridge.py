"""WP-090: Proof Bridge tests — promote, eligibility, lineage."""

from __future__ import annotations

from notary_platform.discovery.models import DecisionEvidenceRecord
from notary_platform.sweep.bridge import ProofBridgeService
from notary_platform.sweep.models import (
    AssuranceCandidate,
    PromotionDelegation,
    ReviewDecision,
    SweepDefinition,
    SweepRun,
)
from notary_platform.storage import get_storage, reset_storage
from notary_platform.sweep.evaluators.base import FrozenDecisionEvidenceRecord
from notary_platform.sweep.candidates import CandidateReviewService


def _setup_candidate(
    org_id: str = "test-org",
    evidence_level: str = "E3",
    lifecycle_state: str = "reviewable",
    der_id: str = "der-test-1",
    with_review: bool = True,
) -> tuple[AssuranceCandidate, DecisionEvidenceRecord]:
    s = get_storage()
    der = DecisionEvidenceRecord(
        id=der_id,
        org_id=org_id,
        decision_identity="res-1",
        identity_method="dep_link_assertion",
        source_resource_ids=["src-1"],
        context_binding_ids=["cb-1"],
        resolution_trace_id="rt-1",
    )
    s.create_decision_evidence_record(der)

    sd = SweepDefinition(id="sd-1", org_id=org_id, name="test-def")
    s.create_sweep_definition(sd)
    run = SweepRun(id="sr-1", org_id=org_id, definition_id="sd-1")
    s.create_sweep_run(run)

    candidate = AssuranceCandidate(
        id="ac-1",
        org_id=org_id,
        der_id=der_id,
        sweep_run_id="sr-1",
        candidate_type="missing_evidence",
        evidence_level=evidence_level,
        lifecycle_state=lifecycle_state,
        actual_outcome="fail",
        expected_outcome="pass",
        missing_prerequisites=["cassette_001"],
    )
    s.create_assurance_candidate(candidate)

    if with_review:
        review = ReviewDecision(
            candidate_id=candidate.id,
            org_id=org_id,
            actor="analyst-1",
            role="reviewer",
            decision="approve_incident",
            basis="looks good",
        )
        s.create_review_decision(review)

    return candidate, der


class TestProofBridgeService:
    def test_eligibility_no_candidate(self) -> None:
        reset_storage()
        svc = ProofBridgeService(get_storage())
        result = svc.check_eligibility("ac-nonexistent", "test-org")
        assert not result["eligible"]
        assert "not found" in result["reason"]

    def test_eligibility_wrong_org(self) -> None:
        reset_storage()
        s = get_storage()
        c = AssuranceCandidate(id="ac-1", org_id="org-a", der_id="der-1")
        s.create_assurance_candidate(c)
        svc = ProofBridgeService(s)
        result = svc.check_eligibility("ac-1", "org-b")
        assert not result["eligible"]

    def test_eligibility_missing_review(self) -> None:
        reset_storage()
        _setup_candidate(with_review=False)
        svc = ProofBridgeService(get_storage())
        result = svc.check_eligibility("ac-1", "test-org")
        assert not result["eligible"]
        assert "approved review decision" in result["prerequisites"][0]

    def test_eligibility_evidence_too_low(self) -> None:
        reset_storage()
        _setup_candidate(evidence_level="E1")
        svc = ProofBridgeService(get_storage())
        result = svc.check_eligibility("ac-1", "test-org")
        assert not result["eligible"]
        assert any("E1" in p for p in result["prerequisites"])

    def test_eligibility_passes(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = ProofBridgeService(get_storage())
        result = svc.check_eligibility("ac-1", "test-org")
        assert result["eligible"]
        assert result["evidence_level"] == "E3"

    def test_eligibility_with_delegation(self) -> None:
        reset_storage()
        _setup_candidate()
        s = get_storage()
        delegation = PromotionDelegation(
            org_id="test-org",
            name="auto-approve",
            rule_type="deterministic",
            conditions={"evidence_level": "E3"},
            scope="missing_evidence",
        )
        s.create_promotion_delegation(delegation)
        svc = ProofBridgeService(s)
        result = svc.check_eligibility("ac-1", "test-org")
        assert result["eligible"]
        assert result["delegation"] is not None
        assert result["delegation"]["name"] == "auto-approve"

    def test_eligibility_approved_incident_skips_review_check(self) -> None:
        reset_storage()
        _setup_candidate(lifecycle_state="approved_incident", with_review=False)
        svc = ProofBridgeService(get_storage())
        result = svc.check_eligibility("ac-1", "test-org")
        assert result["eligible"]

    def test_promote_creates_vr(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = ProofBridgeService(get_storage())
        result = svc.promote("ac-1", "test-org")
        assert result["success"]
        assert result["bridge_key"] == "bridge-test-org-der-test-1"
        assert result["is_new_record"]
        assert result["verification_record_id"].startswith("vr-")
        assert result["evidence_bundle_ref"].startswith("eb-")
        assert result["incident_ref"] == ""

        s = get_storage()
        vr = s.get_vr(result["verification_record_id"])
        assert vr is not None
        assert vr.bridge_key == result["bridge_key"]
        assert vr.processing_path == "sweep_bridge"

    def test_promote_idempotent(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = ProofBridgeService(get_storage())
        r1 = svc.promote("ac-1", "test-org")
        r2 = svc.promote("ac-1", "test-org")
        assert r1["success"]
        assert r2["success"]
        assert r1["verification_record_id"] == r2["verification_record_id"]
        assert not r2["is_new_record"]

    def test_promote_approved_incident_creates_incident(self) -> None:
        reset_storage()
        _setup_candidate(lifecycle_state="approved_incident")
        svc = ProofBridgeService(get_storage())
        result = svc.promote("ac-1", "test-org")
        assert result["success"]
        assert result["incident_ref"].startswith("inc-")

        s = get_storage()
        vr = s.get_vr(result["verification_record_id"])
        assert vr is not None
        assert vr.promoted_to_incident == result["incident_ref"]

    def test_promote_no_review_fails(self) -> None:
        reset_storage()
        _setup_candidate(with_review=False)
        svc = ProofBridgeService(get_storage())
        result = svc.promote("ac-1", "test-org")
        assert not result["success"]

    def test_lineage_returns_full_history(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = ProofBridgeService(get_storage())
        svc.promote("ac-1", "test-org")
        lineage = svc.get_lineage("ac-1", "test-org")
        assert "candidate" in lineage
        assert "decision_evidence_record" in lineage
        assert "reviews" in lineage
        assert "lineage" in lineage
        steps = [s["step"] for s in lineage["lineage"]]
        assert "proof_bridge" in steps
        assert len(lineage["proof_loop_records"]) == 1

    def test_lineage_no_candidate(self) -> None:
        reset_storage()
        svc = ProofBridgeService(get_storage())
        assert svc.get_lineage("ac-nonexistent", "test-org") == {}

    def test_promote_stores_evidence_bundle(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = ProofBridgeService(get_storage())
        result = svc.promote("ac-1", "test-org")
        bundle_ref = result["evidence_bundle_ref"]
        s = get_storage()
        bundles = s._evidence  # in-memory evidence dict
        assert bundle_ref in bundles
        bundle = bundles[bundle_ref]
        assert bundle["candidate_id"] == "ac-1"
        assert bundle["bridge_key"] == "bridge-test-org-der-test-1"
        assert bundle["declared_omissions"] == ["cassette_001"]
        assert bundle["evidence_level"] == "E3"
