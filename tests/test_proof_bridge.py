"""WP-090: Proof Bridge tests — promote, eligibility, lineage."""

from __future__ import annotations

from notary_platform.dep.registry import SchemaRegistry
from notary_platform.discovery.models import DecisionEvidenceRecord, DecisionEvidenceResource
from notary_platform.models import (
    MutationTest,
    ReadinessCheck,
    ReleaseGateResult,
    ReplayRun,
    Scenario,
    ScenarioRun,
)
from notary_platform.services import IngestionService, ServiceRegistry
from notary_platform.storage import StorageBackend, get_storage, reset_storage
from notary_platform.sweep.bridge import ProofBridgeService
from notary_platform.sweep.models import (
    AssuranceCandidate,
    PromotionDelegation,
    ReviewDecision,
    SweepDefinition,
    SweepRun,
)


def _service(storage: StorageBackend | None = None) -> ProofBridgeService:
    selected = storage or get_storage()
    return ProofBridgeService(selected, IngestionService(ServiceRegistry(selected)))


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
        environment_id="env-test",
        decision_identity="res-1",
        identity_method="dep_link_assertion",
        source_resource_ids=["urn:notary:resource:src-1"],
        resolution_trace_id="rt-1",
    )
    s.create_decision_evidence_record(der)
    s.create_resource(
        DecisionEvidenceResource(
            resource_id="urn:notary:resource:src-1",
            org_id=org_id,
            environment_id="env-test",
            envelope_id="urn:notary:envelope:src-1",
            resource_type="observation",
            provider_id="urn:notary:provider:test",
            digest_algorithm="sha256",
            digest_value="a" * 64,
            payload_ref="urn:notary:payload:src-1",
        )
    )

    sd = SweepDefinition(id="sd-1", org_id=org_id, name="test-def", environment_id="env-test")
    s.create_sweep_definition(sd)
    run = SweepRun(id="sr-1", org_id=org_id, environment_id="env-test", definition_id="sd-1")
    s.create_sweep_run(run)

    candidate = AssuranceCandidate(
        id="ac-1",
        org_id=org_id,
        environment_id="env-test",
        der_id=der_id,
        sweep_run_id="sr-1",
        candidate_type="missing_evidence",
        supporting_resource_ids=["urn:notary:resource:src-1"],
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
            environment_id="env-test",
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
        svc = _service()
        result = svc.check_eligibility("ac-nonexistent", "test-org")
        assert not result["eligible"]
        assert "not found" in result["reason"]

    def test_eligibility_wrong_org(self) -> None:
        reset_storage()
        s = get_storage()
        c = AssuranceCandidate(id="ac-1", org_id="org-a", der_id="der-1")
        s.create_assurance_candidate(c)
        svc = _service(s)
        result = svc.check_eligibility("ac-1", "org-b")
        assert not result["eligible"]

    def test_eligibility_missing_review(self) -> None:
        reset_storage()
        _setup_candidate(with_review=False)
        svc = _service()
        result = svc.check_eligibility("ac-1", "test-org")
        assert not result["eligible"]
        assert "approved review decision" in result["prerequisites"][0]

    def test_eligibility_evidence_too_low(self) -> None:
        reset_storage()
        _setup_candidate(evidence_level="E1")
        svc = _service()
        result = svc.check_eligibility("ac-1", "test-org")
        assert not result["eligible"]
        assert any("E1" in p for p in result["prerequisites"])

    def test_eligibility_passes(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        result = svc.check_eligibility("ac-1", "test-org")
        assert result["eligible"]
        assert result["evidence_level"] == "E3"

    def test_eligibility_with_delegation(self) -> None:
        reset_storage()
        _setup_candidate(with_review=False)
        s = get_storage()
        delegation = PromotionDelegation(
            org_id="test-org",
            environment_id="env-test",
            name="auto-approve",
            rule_type="deterministic",
            conditions={"evidence_level": "E3"},
            scope="missing_evidence",
        )
        s.create_promotion_delegation(delegation)
        svc = _service(s)
        result = svc.check_eligibility("ac-1", "test-org")
        assert result["eligible"]
        assert result["delegation"] is not None
        assert result["delegation"]["name"] == "auto-approve"

    def test_eligibility_approved_incident_skips_review_check(self) -> None:
        reset_storage()
        _setup_candidate(lifecycle_state="approved_incident", with_review=False)
        svc = _service()
        result = svc.check_eligibility("ac-1", "test-org")
        assert not result["eligible"]
        assert result["error_code"] == "PROMOTION_AUTHORITY_MISSING"

    def test_promote_creates_vr(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        result = svc.promote("ac-1", "test-org")
        assert result["success"]
        assert result["bridge_key"].startswith("bridge-")
        assert result["is_new_record"]
        assert result["verification_record_id"].startswith("vr-")
        assert result["evidence_bundle_ref"].startswith("urn:notary:evidence-bundle:")
        assert result["incident_ref"].startswith("inc-")
        assert result["replay_state"] in {
            "fully_replayable",
            "partially_replayable",
            "requires_sandbox",
            "not_replayable",
            "missing_evidence",
        }

        s = get_storage()
        vr = s.get_vr(result["verification_record_id"])
        assert vr is not None
        assert vr.bridge_key == result["bridge_key"]
        assert vr.processing_path == "sweep_bridge"

    def test_promote_idempotent(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        r1 = svc.promote("ac-1", "test-org")
        r2 = svc.promote("ac-1", "test-org")
        assert r1["success"]
        assert r2["success"]
        assert r1["verification_record_id"] == r2["verification_record_id"]
        assert r1["incident_ref"] == r2["incident_ref"]
        assert r1["evidence_bundle_ref"] == r2["evidence_bundle_ref"]
        assert not r2["is_new_record"]

    def test_distinct_candidates_from_same_der_get_distinct_proof_records(self) -> None:
        reset_storage()
        candidate, _ = _setup_candidate()
        second = AssuranceCandidate.from_dict({**candidate.to_dict(), "id": "ac-2"})
        get_storage().create_assurance_candidate(second)
        get_storage().create_review_decision(
            ReviewDecision(
                candidate_id=second.id,
                org_id=second.org_id,
                environment_id=second.environment_id,
                actor="analyst-2",
                role="reviewer",
                decision="approve_incident",
                basis="independent candidate",
            )
        )
        service = _service()
        first_result = service.promote(candidate.id, candidate.org_id)
        second_result = service.promote(second.id, second.org_id)
        assert first_result["verification_record_id"] != second_result["verification_record_id"]
        assert first_result["incident_ref"] != second_result["incident_ref"]

    def test_promote_approved_incident_creates_incident(self) -> None:
        reset_storage()
        _setup_candidate(lifecycle_state="approved_incident")
        svc = _service()
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
        svc = _service()
        result = svc.promote("ac-1", "test-org")
        assert not result["success"]

    def test_lineage_returns_full_history(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        promoted = svc.promote("ac-1", "test-org")
        storage = get_storage()
        storage.create_scenario(
            Scenario(
                id="scenario-bridge",
                org_id="test-org",
                environment_id="env-test",
                source_vr_id=promoted["verification_record_id"],
                source_incident_id=promoted["incident_ref"],
            )
        )
        storage.create_scenario_run(
            ScenarioRun(
                id="run-bridge",
                org_id="test-org",
                environment_id="env-test",
                scenario_ids=["scenario-bridge"],
            )
        )
        storage.create_readiness_check(
            ReadinessCheck(
                id="readiness-bridge",
                org_id="test-org",
                environment_id="env-test",
                scenario_run_id="run-bridge",
            )
        )
        storage.create_release_gate_result(
            ReleaseGateResult(
                id="gate-bridge",
                org_id="test-org",
                readiness_check_id="readiness-bridge",
                scenario_run_id="run-bridge",
            )
        )
        lineage = svc.get_lineage("ac-1", "test-org")
        assert "candidate" in lineage
        assert "decision_evidence_record" in lineage
        assert "reviews" in lineage
        assert "lineage" in lineage
        steps = [s["step"] for s in lineage["lineage"]]
        assert "proof_bridge" in steps
        assert len(lineage["proof_loop_records"]) == 1
        proof = lineage["proof_loop_records"][0]
        assert [item["id"] for item in proof["scenario_runs"]] == ["run-bridge"]
        assert [item["id"] for item in proof["readiness_checks"]] == ["readiness-bridge"]
        assert [item["id"] for item in proof["release_gates"]] == ["gate-bridge"]

    def test_lineage_no_candidate(self) -> None:
        reset_storage()
        svc = _service()
        assert svc.get_lineage("ac-nonexistent", "test-org") == {}

    def test_promote_stores_evidence_bundle(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        result = svc.promote("ac-1", "test-org")
        bundle_ref = result["evidence_bundle_ref"]
        s = get_storage()
        bundles = s._evidence  # in-memory evidence dict
        assert bundle_ref in bundles
        bundle = bundles[bundle_ref]
        extension = bundle["extensions"]["urn:notary:proof-bridge"]
        assert extension["candidate_id"] == "ac-1"
        assert extension["bridge_key"] == result["bridge_key"]
        assert bundle["declared_omissions"] == ["cassette_001"]
        assert extension["evidence_level"] == "E3"
        assert bundle["manifest_digest"]["algorithm"] == "sha-256"
        assert bundle["subjects"] == [
            {
                "resource_ref": "urn:notary:resource:src-1",
                "digest": {"algorithm": "sha-256", "value": "a" * 64},
            }
        ]
        assert SchemaRegistry().validate(bundle, "evidence-bundle") == []
        assert SchemaRegistry().validate({**bundle, "unexpected": True}, "evidence-bundle")

    def test_missing_environment_scope_is_rejected(self) -> None:
        reset_storage()
        candidate, _ = _setup_candidate()
        candidate.environment_id = ""
        get_storage().update_assurance_candidate(candidate)
        result = _service().check_eligibility(candidate.id, candidate.org_id)
        assert not result["eligible"]
        assert "ENVIRONMENT_SCOPE_MISMATCH" in {failure["code"] for failure in result["failures"]}

    def test_e2_candidate_gets_enrichment_action(self) -> None:
        reset_storage()
        _setup_candidate(evidence_level="E2")
        result = _service().check_eligibility("ac-1", "test-org")
        assert not result["eligible"]
        assert "enrich_evidence_to_E3" in result["next_actions"]

    def test_later_dismissal_revokes_historical_approval(self) -> None:
        reset_storage()
        candidate, _ = _setup_candidate()
        get_storage().create_review_decision(
            ReviewDecision(
                candidate_id=candidate.id,
                org_id=candidate.org_id,
                environment_id=candidate.environment_id,
                actor="reviewer-2",
                role="reviewer",
                decision="dismiss",
                basis="superseding disposition",
                created_at="9999-01-01T00:00:00+00:00",
            )
        )
        result = _service().check_eligibility(candidate.id, candidate.org_id)
        assert not result["eligible"]
        assert "PROMOTION_AUTHORITY_MISSING" in {failure["code"] for failure in result["failures"]}

    def test_cross_org_der_is_rejected(self) -> None:
        reset_storage()
        candidate, der = _setup_candidate()
        der.org_id = "other-org"
        get_storage().create_decision_evidence_record(der)
        result = _service().check_eligibility(candidate.id, candidate.org_id)
        assert not result["eligible"]
        assert "ORGANIZATION_SCOPE_MISMATCH" in {failure["code"] for failure in result["failures"]}

    def test_incident_records_promotion_lineage(self) -> None:
        reset_storage()
        _setup_candidate()
        result = _service().promote("ac-1", "test-org")
        incident = get_storage().get_incident(result["incident_ref"])
        assert incident is not None
        lineage = incident.snapshot_summary["proof_bridge_lineage"]
        assert lineage["candidate_id"] == "ac-1"
        assert lineage["evidence_bundle_ref"] == result["evidence_bundle_ref"]
        assert lineage["review_decision_id"]

    def test_e4_recalculated_from_verified_proof_loop_not_direct_assignment(self) -> None:
        reset_storage()
        _, der = _setup_candidate(evidence_level="E3")
        svc = _service()
        result = svc.promote("ac-1", "test-org")
        s = get_storage()
        vr = s.get_vr(result["verification_record_id"])
        replay = ReplayRun(
            id="rp-e4-1",
            org_id="test-org",
            verification_record_id=vr.id,
            status="completed",
        )
        s.create_replay_run(replay)
        mutation = MutationTest(
            id="mt-e4-1",
            org_id="test-org",
            verification_record_id=vr.id,
            verdict="verified",
        )
        s.create_mutation_test(mutation)
        recalculated = ProofBridgeService._recalculate_evidence_level(svc, "ac-1", "test-org", result["bridge_key"])
        assert recalculated == "E4"
        assert recalculated != "E3"

    def test_e4_stays_e3_when_verification_incomplete(self) -> None:
        reset_storage()
        _setup_candidate(evidence_level="E3")
        svc = _service()
        result = svc.promote("ac-1", "test-org")
        s = get_storage()
        vr = s.get_vr(result["verification_record_id"])
        replay = ReplayRun(
            id="rp-e4-2",
            org_id="test-org",
            verification_record_id=vr.id,
            status="completed",
        )
        s.create_replay_run(replay)
        recalculated = ProofBridgeService._recalculate_evidence_level(svc, "ac-1", "test-org", result["bridge_key"])
        assert recalculated == "E3"

    def test_evidence_bundle_digest_verification(self) -> None:
        reset_storage()
        _setup_candidate()
        result = _service().promote("ac-1", "test-org")
        s = get_storage()
        bundle = s._evidence[result["evidence_bundle_ref"]]
        assert ProofBridgeService._verify_bundle_digest(bundle)
        bundle["manifest_digest"]["value"] = "tampered"
        assert not ProofBridgeService._verify_bundle_digest(bundle)

    def test_lineage_filters_by_environment_scope(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        promoted = svc.promote("ac-1", "test-org")
        s = get_storage()
        s.create_scenario(
            Scenario(
                id="scenario-env-a",
                org_id="test-org",
                environment_id="env-test",
                source_vr_id=promoted["verification_record_id"],
                source_incident_id=promoted["incident_ref"],
            )
        )
        s.create_scenario(
            Scenario(
                id="scenario-other-env",
                org_id="test-org",
                environment_id="other-env",
                source_vr_id=promoted["verification_record_id"],
                source_incident_id=promoted["incident_ref"],
            )
        )
        lineage = svc.get_lineage("ac-1", "test-org")
        proof = lineage["proof_loop_records"][0]
        scenario_ids = {item["id"] for item in proof["scenarios"]}
        assert "scenario-env-a" in scenario_ids
        assert "scenario-other-env" not in scenario_ids

    def test_full_gate_lineage_integration(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        promoted = svc.promote("ac-1", "test-org")
        s = get_storage()
        s.create_scenario(
            Scenario(
                id="scenario-full-1",
                org_id="test-org",
                environment_id="env-test",
                source_vr_id=promoted["verification_record_id"],
                source_incident_id=promoted["incident_ref"],
            )
        )
        s.create_scenario(
            Scenario(
                id="scenario-full-2",
                org_id="test-org",
                environment_id="env-test",
                source_vr_id=promoted["verification_record_id"],
                source_incident_id=promoted["incident_ref"],
            )
        )
        s.create_scenario_run(
            ScenarioRun(
                id="run-full-1",
                org_id="test-org",
                environment_id="env-test",
                scenario_ids=["scenario-full-1", "scenario-full-2"],
            )
        )
        s.create_readiness_check(
            ReadinessCheck(
                id="readiness-full-1",
                org_id="test-org",
                environment_id="env-test",
                scenario_run_id="run-full-1",
            )
        )
        s.create_release_gate_result(
            ReleaseGateResult(
                id="gate-full-1",
                org_id="test-org",
                readiness_check_id="readiness-full-1",
                scenario_run_id="run-full-1",
            )
        )
        lineage = svc.get_lineage("ac-1", "test-org")
        assert len(lineage["proof_loop_records"]) == 1
        proof = lineage["proof_loop_records"][0]
        assert {item["id"] for item in proof["scenarios"]} == {"scenario-full-1", "scenario-full-2"}
        assert [item["id"] for item in proof["scenario_runs"]] == ["run-full-1"]
        assert [item["id"] for item in proof["readiness_checks"]] == ["readiness-full-1"]
        assert [item["id"] for item in proof["release_gates"]] == ["gate-full-1"]

    def test_authority_fails_closed_on_cross_env_delegation(self) -> None:
        reset_storage()
        _setup_candidate(with_review=False)
        s = get_storage()
        delegation = PromotionDelegation(
            org_id="test-org",
            environment_id="wrong-env",
            name="cross-env",
            rule_type="deterministic",
            conditions={"evidence_level": "E3", "org_id": "test-org"},
        )
        s.create_promotion_delegation(delegation)
        result = _service(s).check_eligibility("ac-1", "test-org")
        assert not result["eligible"]
        assert "PROMOTION_AUTHORITY_MISSING" in {f["code"] for f in result["failures"]}

    def test_promotion_retry_idempotent_same_bridge_key(self) -> None:
        reset_storage()
        _setup_candidate()
        svc = _service()
        r1 = svc.promote("ac-1", "test-org")
        r2 = svc.promote("ac-1", "test-org")
        assert r1["success"]
        assert r2["success"]
        assert r1["bridge_key"] == r2["bridge_key"]
        assert r1["verification_record_id"] == r2["verification_record_id"]
        assert r1["incident_ref"] == r2["incident_ref"]
        assert r2["is_new_record"] is False
