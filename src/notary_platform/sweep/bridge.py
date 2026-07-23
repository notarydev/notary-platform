from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from notary_platform.models import DataSourceType, EvidenceArtifact, ReplayabilityStatus, VerificationRecord
from notary_platform.sweep.models import AssuranceCandidate, PromotionDelegation, ReviewDecision


class ProofBridgeService:
    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def check_eligibility(self, candidate_id: str, org_id: str) -> dict[str, Any]:
        candidate = self._storage.get_assurance_candidate(candidate_id)
        if candidate is None or candidate.org_id != org_id:
            return {"eligible": False, "reason": "candidate not found", "prerequisites": []}

        missing: list[str] = []
        if candidate.lifecycle_state not in ("approved_incident",):
            reviews = self._storage.list_review_decisions(candidate_id)
            approved = [r for r in reviews if r.decision == "approve_incident"]
            if not approved:
                missing.append("approved review decision")

        if candidate.evidence_level in ("", "E0", "E1"):
            missing.append(f"evidence level {candidate.evidence_level} too low; E2+ required")

        der = self._storage.get_decision_evidence_record(candidate.der_id) if candidate.der_id else None
        if der is None:
            missing.append("decision evidence record not found")

        if missing:
            return {
                "eligible": False,
                "reason": "missing prerequisites",
                "prerequisites": missing,
                "evidence_level": candidate.evidence_level,
                "lifecycle_state": candidate.lifecycle_state,
            }

        delegation = self._check_delegation(candidate, org_id)
        return {
            "eligible": True,
            "reason": "",
            "prerequisites": [],
            "evidence_level": candidate.evidence_level,
            "lifecycle_state": candidate.lifecycle_state,
            "delegation": delegation.to_dict() if delegation else None,
        }

    def promote(self, candidate_id: str, org_id: str) -> dict[str, Any]:
        eligibility = self.check_eligibility(candidate_id, org_id)
        if not eligibility["eligible"]:
            return {"success": False, "error": eligibility["reason"], "prerequisites": eligibility.get("prerequisites", [])}

        candidate = self._storage.get_assurance_candidate(candidate_id)
        der = self._storage.get_decision_evidence_record(candidate.der_id)

        bridge_key = f"bridge-{candidate.org_id}-{candidate.der_id}"

        existing_vrs = self._storage.list_vrs_by_bridge_key(bridge_key, org_id)
        if existing_vrs:
            vr = existing_vrs[0]
            is_new = False
        else:
            is_new = True
            vr = self._create_vr_for_candidate(candidate, der, bridge_key)

        evidence_bundle = self._freeze_evidence_bundle(candidate, der, bridge_key)
        bundle_ref = self._storage.store_evidence_bundle(evidence_bundle, org_id)

        incident_ref = ""
        if candidate.lifecycle_state == "approved_incident":
            inc = self._storage.create_incident({"elements": []}, org_id=org_id)
            vr.promoted_to_incident = inc.incident_id
            self._storage.update_vr(vr)
            incident_ref = inc.incident_id

        return {
            "success": True,
            "bridge_key": bridge_key,
            "verification_record_id": vr.id,
            "is_new_record": is_new,
            "evidence_bundle_ref": bundle_ref,
            "incident_ref": incident_ref,
            "replay_state": vr.replayability.value if vr.replayability else "unknown",
            "replayability_reason": vr.replayability_reason,
            "missing_prerequisites": list(vr.missing_prerequisites),
            "candidate_id": candidate.id,
            "der_id": candidate.der_id,
            "sweep_run_id": candidate.sweep_run_id,
        }

    def get_lineage(self, candidate_id: str, org_id: str) -> dict[str, Any]:
        candidate = self._storage.get_assurance_candidate(candidate_id)
        if candidate is None or candidate.org_id != org_id:
            return {}

        der = self._storage.get_decision_evidence_record(candidate.der_id) if candidate.der_id else None
        sweep_run = self._storage.get_sweep_run(candidate.sweep_run_id) if candidate.sweep_run_id else None
        definition = self._storage.get_sweep_definition(sweep_run.definition_id) if sweep_run else None
        reviews = self._storage.list_review_decisions(candidate_id)

        assessments = []
        for aid in candidate.assessment_ids:
            a = self._storage.get_assessment(aid)
            if a:
                assessments.append(a.to_dict())

        vrs = self._storage.list_vrs_by_bridge_key(f"bridge-{org_id}-{candidate.der_id}", org_id) if candidate.der_id else []

        return {
            "candidate": candidate.to_dict(),
            "sweep_run": sweep_run.to_dict() if sweep_run else None,
            "sweep_definition": definition.to_dict() if definition else None,
            "decision_evidence_record": der.to_dict() if der else None,
            "reviews": [r.to_dict() for r in reviews],
            "assessments": assessments,
            "proof_loop_records": [vr.to_dict() for vr in vrs],
            "lineage": [
                {"step": "source_ingestion", "refs": list(der.source_resource_ids) if der else []},
                {"step": "identity_resolution", "method": der.identity_method if der else "", "identity": der.decision_identity if der else ""},
                {"step": "context_resolution", "trace_id": der.resolution_trace_id if der else ""},
                {"step": "sweep_evaluation", "run_id": candidate.sweep_run_id},
                {"step": "candidate_assembly", "candidate_id": candidate.id, "type": candidate.candidate_type, "state": candidate.lifecycle_state},
                {"step": "review", "review_count": len(reviews)},
                {"step": "proof_bridge", "proof_loop_records": len(vrs)},
            ],
        }

    def _create_vr_for_candidate(self, candidate: AssuranceCandidate, der: Any, bridge_key: str) -> VerificationRecord:
        vr = VerificationRecord(
            id=f"vr-{uuid.uuid4().hex[:8]}",
            org_id=candidate.org_id,
            environment_id=candidate.environment_id,
            source_type=DataSourceType.sdk_snapshot,
            source_system_id="proof_bridge",
            source_record_ref=candidate.der_id,
            bridge_key=bridge_key,
            agent_id=candidate.der_id,
            business_function=candidate.candidate_type,
            expected_outcome=candidate.expected_outcome or "",
            root_hash=bridge_key,
            processing_path="sweep_bridge",
        )
        artifact = EvidenceArtifact(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            org_id=candidate.org_id,
            verification_record_id=vr.id,
            kind="snapshot",
            reference="",
            payload={
                "candidate_id": candidate.id,
                "der_id": candidate.der_id,
                "sweep_run_id": candidate.sweep_run_id,
                "evidence_level": candidate.evidence_level,
                "candidate_type": candidate.candidate_type,
                "actual_outcome": candidate.actual_outcome,
                "expected_outcome": candidate.expected_outcome,
            },
        )
        self._storage.create_evidence_artifact(artifact)
        vr.replayability = ReplayabilityStatus.unknown
        vr.replayability_reason = "pending replay assessment"
        vr.computed_replayability = ReplayabilityStatus.unknown
        vr.replayability_source = "computed"
        return self._storage.create_vr(vr)

    def _freeze_evidence_bundle(self, candidate: AssuranceCandidate, der: Any, bridge_key: str) -> dict[str, Any]:
        return {
            "bundle_id": f"eb-{uuid.uuid4().hex[:12]}",
            "bridge_key": bridge_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "candidate_id": candidate.id,
            "der_id": candidate.der_id,
            "sweep_run_id": candidate.sweep_run_id,
            "evidence_level": candidate.evidence_level,
            "candidate_type": candidate.candidate_type,
            "source_resource_ids": list(der.source_resource_ids) if der else [],
            "context_binding_ids": list(der.context_binding_ids) if der else [],
            "resolution_trace_id": der.resolution_trace_id if der else "",
            "assessment_ids": list(candidate.assessment_ids),
            "declared_omissions": list(candidate.missing_prerequisites),
            "sealed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _check_delegation(self, candidate: AssuranceCandidate, org_id: str) -> PromotionDelegation | None:
        delegations = self._storage.list_promotion_delegations(org_id)
        for d in delegations:
            if not d.active:
                continue
            if d.rule_type == "deterministic":
                scope_match = not d.scope or d.scope == candidate.candidate_type
                ev_match = not d.conditions.get("evidence_level") or d.conditions["evidence_level"] == candidate.evidence_level
                if scope_match and ev_match:
                    return d
        return None
