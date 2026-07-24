from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from notary_platform.models import EvidenceBundle, Incident, ReplayabilityStatus, VerificationRecord
from notary_platform.sweep.models import AssuranceCandidate, PromotionDelegation
from notary_platform.sweep.sufficiency import EvidenceSufficiencyService

if TYPE_CHECKING:
    from notary_platform.services import IngestionService


_PUBLIC_REPLAY_STATES = {
    ReplayabilityStatus.replayable: "fully_replayable",
    ReplayabilityStatus.partially_replayable: "partially_replayable",
    ReplayabilityStatus.requires_sandbox: "requires_sandbox",
    ReplayabilityStatus.evidence_only: "not_replayable",
    ReplayabilityStatus.blocked: "not_replayable",
    ReplayabilityStatus.missing_context: "missing_evidence",
    ReplayabilityStatus.requires_human_label: "missing_evidence",
    ReplayabilityStatus.unknown: "missing_evidence",
}


class ProofBridgeService:
    def __init__(self, storage: Any, ingestion_service: IngestionService) -> None:
        self._storage = storage
        self._ingestion = ingestion_service

    def check_eligibility(self, candidate_id: str, org_id: str) -> dict[str, Any]:
        candidate = self._storage.get_assurance_candidate(candidate_id)
        if candidate is None or candidate.org_id != org_id:
            return self._blocked(
                "CANDIDATE_NOT_FOUND",
                "candidate not found",
                "verify_candidate_id",
            )

        failures: list[dict[str, str]] = []
        der = self._storage.get_decision_evidence_record(candidate.der_id) if candidate.der_id else None
        if der is None:
            failures.append(
                self._failure(
                    "DECISION_EVIDENCE_RECORD_MISSING",
                    "decision evidence record not found",
                    "rebuild_decision_evidence_record",
                )
            )
        elif der.org_id != org_id:
            failures.append(
                self._failure(
                    "ORGANIZATION_SCOPE_MISMATCH",
                    "decision evidence record is outside the candidate organization",
                    "correct_candidate_lineage",
                )
            )
        elif not der.environment_id or der.environment_id != candidate.environment_id:
            failures.append(
                self._failure(
                    "ENVIRONMENT_SCOPE_MISMATCH",
                    "decision evidence record is outside the candidate environment",
                    "correct_candidate_lineage",
                )
            )

        sweep_run = self._storage.get_sweep_run(candidate.sweep_run_id) if candidate.sweep_run_id else None
        if sweep_run is None:
            failures.append(self._failure("SWEEP_RUN_MISSING", "sweep run not found", "restore_sweep_run_lineage"))
        elif sweep_run.org_id != org_id:
            failures.append(
                self._failure(
                    "ORGANIZATION_SCOPE_MISMATCH",
                    "sweep run is outside the candidate organization",
                    "correct_candidate_lineage",
                )
            )
        elif not sweep_run.environment_id or sweep_run.environment_id != candidate.environment_id:
            failures.append(
                self._failure(
                    "ENVIRONMENT_SCOPE_MISMATCH",
                    "sweep run is outside the candidate environment",
                    "correct_candidate_lineage",
                )
            )
        else:
            definition = self._storage.get_sweep_definition(sweep_run.definition_id)
            if definition is None:
                failures.append(
                    self._failure(
                        "SWEEP_DEFINITION_MISSING",
                        "sweep definition not found",
                        "restore_sweep_definition_lineage",
                    )
                )
            elif (
                definition.org_id != org_id
                or not candidate.environment_id
                or not definition.environment_id
                or candidate.environment_id != definition.environment_id
            ):
                failures.append(
                    self._failure(
                        "ENVIRONMENT_SCOPE_MISMATCH",
                        "candidate and sweep definition scopes do not match",
                        "correct_candidate_environment",
                    )
                )

        if candidate.evidence_level not in ("E3", "E4"):
            action = "enrich_evidence_to_E3" if candidate.evidence_level in ("E1", "E2") else "instrument_next_occurrence"
            failures.append(
                self._failure(
                    "EVIDENCE_LEVEL_INSUFFICIENT",
                    f"evidence level {candidate.evidence_level or 'E0'} is below E3",
                    action,
                )
            )

        resource_ids = self._supporting_resource_ids(candidate, der)
        if not resource_ids:
            failures.append(
                self._failure(
                    "SUPPORTING_EVIDENCE_MISSING",
                    "no supporting evidence resources are linked",
                    "attach_supporting_evidence",
                )
            )
        else:
            for resource_id in resource_ids:
                resource = self._storage.get_resource(resource_id, org_id)
                if resource is None:
                    failures.append(
                        self._failure(
                            "SUPPORTING_RESOURCE_MISSING",
                            f"supporting resource not found: {resource_id}",
                            "restore_or_reingest_supporting_resource",
                        )
                    )
                elif not resource.environment_id or resource.environment_id != candidate.environment_id:
                    failures.append(
                        self._failure(
                            "ENVIRONMENT_SCOPE_MISMATCH",
                            f"supporting resource is outside the candidate environment: {resource_id}",
                            "correct_candidate_lineage",
                        )
                    )

        if der is not None:
            for binding_id in der.context_binding_ids:
                binding = self._storage.get_context_binding(binding_id)
                if binding is None or binding.org_id != org_id or not binding.environment_id or binding.environment_id != candidate.environment_id:
                    failures.append(
                        self._failure(
                            "ENVIRONMENT_SCOPE_MISMATCH",
                            f"context binding is outside the candidate environment: {binding_id}",
                            "correct_context_binding",
                        )
                    )

        authority = self._resolve_authority(candidate, org_id)
        if authority is None:
            failures.append(
                self._failure(
                    "PROMOTION_AUTHORITY_MISSING",
                    "active approved review decision or matching deterministic delegation required",
                    "record_approval_or_create_delegation",
                )
            )

        if failures:
            return {
                "eligible": False,
                "error_code": failures[0]["code"] if len(failures) == 1 else "PROOF_PREREQUISITES_MISSING",
                "reason": "missing proof prerequisites",
                "next_actions": list(dict.fromkeys(item["next_action"] for item in failures)),
                "prerequisites": [item["prerequisite"] for item in failures],
                "failures": failures,
                "evidence_level": candidate.evidence_level,
                "lifecycle_state": candidate.lifecycle_state,
                "authority": None,
            }

        assert authority is not None
        return {
            "eligible": True,
            "error_code": None,
            "reason": "",
            "next_actions": [],
            "prerequisites": [],
            "failures": [],
            "evidence_level": candidate.evidence_level,
            "lifecycle_state": candidate.lifecycle_state,
            "authority": authority,
            "delegation": authority["record"] if authority["kind"] == "delegation" else None,
        }

    def promote(self, candidate_id: str, org_id: str) -> dict[str, Any]:
        eligibility = self.check_eligibility(candidate_id, org_id)
        if not eligibility["eligible"]:
            return {
                "success": False,
                "error": eligibility["reason"],
                "error_code": eligibility["error_code"],
                "next_actions": eligibility["next_actions"],
                "prerequisites": eligibility["prerequisites"],
                "failures": eligibility.get("failures", []),
            }

        candidate = self._storage.get_assurance_candidate(candidate_id)
        der = self._storage.get_decision_evidence_record(candidate.der_id)
        bridge_key = self._bridge_key(candidate)
        existing_vrs = self._storage.list_vrs_by_bridge_key(bridge_key, org_id)
        if existing_vrs:
            vr = existing_vrs[0]
            is_new = False
            incident = self._storage.get_incident(vr.promoted_to_incident) if vr.promoted_to_incident else None
            bundle_ref = incident.snapshot_summary.get("proof_bridge_lineage", {}).get("evidence_bundle_ref", "") if incident is not None else ""
            if not bundle_ref:
                return {
                    "success": False,
                    "error": "existing bridge lineage is incomplete",
                    "error_code": "BRIDGE_LINEAGE_INCOMPLETE",
                    "next_actions": ["repair_bridge_lineage"],
                    "prerequisites": ["immutable evidence bundle reference"],
                }
            evidence_bundle = None
        else:
            evidence_level = self._recalculate_evidence_level(candidate.id, org_id, bridge_key)
            evidence_bundle = self._freeze_evidence_bundle(candidate, der, bridge_key, eligibility["authority"], evidence_level)
            bundle_ref = self._storage.store_evidence_bundle(evidence_bundle.to_dict(), org_id)
            vr = self._create_vr_for_candidate(candidate, evidence_bundle, bridge_key)
            is_new = True

        if vr.promoted_to_incident:
            incident = self._storage.get_incident(vr.promoted_to_incident)
        else:
            incident = self._ingestion.create_incident_from_vr(vr, incident_id=self._incident_id(bridge_key))
        if incident is None or incident.org_id != org_id:
            return {
                "success": False,
                "error": "incident creation failed",
                "error_code": "INCIDENT_CREATION_FAILED",
                "next_actions": ["retry_promotion"],
                "prerequisites": [],
            }

        if is_new:
            assert evidence_bundle is not None
            self._record_incident_lineage(
                incident,
                candidate,
                der,
                bundle_ref,
                eligibility["authority"],
                evidence_bundle.subjects,
            )

        return {
            "success": True,
            "bridge_key": bridge_key,
            "verification_record_id": vr.id,
            "is_new_record": is_new,
            "evidence_bundle_ref": bundle_ref,
            "incident_ref": incident.incident_id,
            "replay_state": self._public_replay_state(vr.replayability),
            "replayability_reason": vr.replayability_reason,
            "missing_prerequisites": list(vr.missing_prerequisites),
            "candidate_id": candidate.id,
            "der_id": candidate.der_id,
            "sweep_run_id": candidate.sweep_run_id,
            "authority": eligibility["authority"],
        }

    def get_lineage(self, candidate_id: str, org_id: str) -> dict[str, Any]:
        candidate = self._storage.get_assurance_candidate(candidate_id)
        if candidate is None or candidate.org_id != org_id:
            return {}

        der = self._storage.get_decision_evidence_record(candidate.der_id) if candidate.der_id else None
        sweep_run = self._storage.get_sweep_run(candidate.sweep_run_id) if candidate.sweep_run_id else None
        definition = self._storage.get_sweep_definition(sweep_run.definition_id) if sweep_run else None
        reviews = [review for review in self._storage.list_review_decisions(candidate_id) if review.org_id == org_id]
        assessments = [
            assessment.to_dict()
            for assessment_id in candidate.assessment_ids
            if (assessment := self._storage.get_assessment(assessment_id)) is not None and assessment.org_id == org_id
        ]
        bridge_key = self._bridge_key(candidate)
        vrs = self._storage.list_vrs_by_bridge_key(bridge_key, org_id) if candidate.der_id else []
        env = candidate.environment_id
        proof_records = []
        for vr in vrs:
            incident = self._storage.get_incident(vr.promoted_to_incident) if vr.promoted_to_incident else None
            replay_runs = [run for run in self._storage.list_replay_runs_for_vr(vr.id) if run.org_id == org_id and (not env or run.environment_id == env)]
            mutation_tests = [
                test for test in self._storage.list_mutation_tests_for_vr(vr.id) if test.org_id == org_id and (not env or test.environment_id == env)
            ]
            scenarios = [
                scenario
                for scenario in self._storage.list_scenarios(org_id, env)
                if scenario.source_vr_id == vr.id or scenario.source_incident_id == vr.promoted_to_incident
            ]
            scenario_ids = {scenario.id for scenario in scenarios}
            scenario_runs = [run for run in self._storage.list_scenario_runs(org_id, env) if scenario_ids.intersection(run.scenario_ids)]
            scenario_run_ids = {run.id for run in scenario_runs}
            readiness_checks = [check for check in self._storage.list_readiness_checks(org_id, env) if check.scenario_run_id in scenario_run_ids]
            readiness_check_ids = {check.id for check in readiness_checks}
            release_gates = [
                gate
                for gate in self._storage.list_release_gate_results(org_id)
                if gate.readiness_check_id in readiness_check_ids or gate.scenario_run_id in scenario_run_ids
            ]
            proof_records.append(
                {
                    "verification_record": vr.to_dict(),
                    "incident": incident.to_dict() if incident and incident.org_id == org_id else None,
                    "replay_runs": [run.to_dict() for run in replay_runs if run.org_id == org_id],
                    "mutation_tests": [test.to_dict() for test in mutation_tests if test.org_id == org_id],
                    "certificate": dict(incident.certificate) if incident and incident.org_id == org_id else {},
                    "scenarios": [scenario.to_dict() for scenario in scenarios],
                    "scenario_runs": [run.to_dict() for run in scenario_runs],
                    "readiness_checks": [check.to_dict() for check in readiness_checks],
                    "release_gates": [gate.to_dict() for gate in release_gates],
                }
            )

        return {
            "candidate": candidate.to_dict(),
            "sweep_run": sweep_run.to_dict() if sweep_run and sweep_run.org_id == org_id else None,
            "sweep_definition": definition.to_dict() if definition and definition.org_id == org_id else None,
            "decision_evidence_record": der.to_dict() if der and der.org_id == org_id else None,
            "reviews": [review.to_dict() for review in reviews],
            "active_authority": self._resolve_authority(candidate, org_id),
            "assessments": assessments,
            "proof_loop_records": proof_records,
            "lineage": [
                {"step": "source_ingestion", "refs": list(der.source_resource_ids) if der and der.org_id == org_id else []},
                {
                    "step": "identity_resolution",
                    "method": der.identity_method if der and der.org_id == org_id else "",
                    "identity": der.decision_identity if der and der.org_id == org_id else "",
                },
                {"step": "context_resolution", "trace_id": der.resolution_trace_id if der and der.org_id == org_id else ""},
                {"step": "sweep_evaluation", "run_id": candidate.sweep_run_id},
                {
                    "step": "candidate_assembly",
                    "candidate_id": candidate.id,
                    "type": candidate.candidate_type,
                    "state": candidate.lifecycle_state,
                },
                {"step": "review", "review_count": len(reviews)},
                {"step": "proof_bridge", "proof_loop_records": len(vrs)},
            ],
        }

    def _create_vr_for_candidate(
        self,
        candidate: AssuranceCandidate,
        bundle: EvidenceBundle,
        bridge_key: str,
    ) -> VerificationRecord:
        snapshot = {
            "schema_version": 1,
            "timestamp": candidate.created_at,
            "elements": [{"kind": "decision", "payload": {"decision": candidate.actual_outcome or "UNKNOWN"}}],
            "merkle_chain": [],
            "root_hash": bundle.manifest_digest["value"],
            "source_system_id": "discovery",
            "source_record_ref": candidate.der_id,
            "business_function": candidate.candidate_type,
            "expected_outcome": candidate.expected_outcome,
            "agent_id": candidate.der_id,
            "environment_id": candidate.environment_id,
            "evidence_bundle_ref": bundle.id,
        }
        vr = self._ingestion.create_from_sdk_snapshot(
            snapshot,
            org_id=candidate.org_id,
            agent_id=candidate.der_id,
            environment_id=candidate.environment_id,
            record_id=self._verification_record_id(bridge_key),
        )
        vr.bridge_key = bridge_key
        vr.processing_path = "sweep_bridge"
        self._storage.update_vr(vr)
        return vr

    def _recalculate_evidence_level(self, candidate_id: str, org_id: str, bridge_key: str) -> str:
        """Recalculate E4 from verified proof-loop state, not from candidate assignment."""
        candidate = self._storage.get_assurance_candidate(candidate_id)
        if candidate is None:
            return ""
        current_level = candidate.evidence_level
        existing_vrs = self._storage.list_vrs_by_bridge_key(bridge_key, org_id)
        has_replay_result = False
        has_verified_mutation = False
        for vr in existing_vrs:
            replay_runs = self._storage.list_replay_runs_for_vr(vr.id)
            if any(run.status in ("replayed", "completed") for run in replay_runs if run.org_id == org_id):
                has_replay_result = True
            mutation_tests = self._storage.list_mutation_tests_for_vr(vr.id)
            if any(test.verdict == "verified" for test in mutation_tests if test.org_id == org_id):
                has_verified_mutation = True
        return EvidenceSufficiencyService.recalculate_after_verification(
            current_level,
            has_replay_result=has_replay_result,
            has_verified_mutation=has_verified_mutation,
        )

    def _freeze_evidence_bundle(
        self,
        candidate: AssuranceCandidate,
        der: Any,
        bridge_key: str,
        authority: dict[str, Any],
        evidence_level: str,
    ) -> EvidenceBundle:
        subjects: list[dict[str, Any]] = []
        for resource_id in self._supporting_resource_ids(candidate, der):
            resource = self._storage.get_resource(resource_id, candidate.org_id)
            if resource is not None:
                subjects.append(
                    {
                        "resource_ref": resource.resource_id,
                        "digest": {
                            "algorithm": self._normalise_digest_algorithm(resource.digest_algorithm),
                            "value": resource.digest_value,
                        },
                    }
                )

        context: list[dict[str, Any]] = []
        for binding_id in der.context_binding_ids:
            binding = self._storage.get_context_binding(binding_id)
            if binding is not None and binding.org_id == candidate.org_id and binding.environment_id == candidate.environment_id:
                context.append(
                    {
                        "binding_id": binding.id,
                        "digest": self._digest_object(binding.to_dict()),
                    }
                )

        evaluator_lineage: list[dict[str, Any]] = []
        for assessment_id in candidate.assessment_ids:
            assessment = self._storage.get_assessment(assessment_id)
            if assessment is not None and assessment.org_id == candidate.org_id:
                evaluator_lineage.append(
                    {
                        "assessment_id": assessment.id,
                        "evaluator_id": assessment.evaluator_id,
                        "evaluator_version": assessment.evaluator_version,
                        "digest": self._digest_object(assessment.to_dict()),
                    }
                )

        created_at = candidate.created_at or datetime.now(timezone.utc).isoformat()
        manifest = {
            "bridge_key": bridge_key,
            "org_id": candidate.org_id,
            "environment_id": candidate.environment_id,
            "candidate_id": candidate.id,
            "candidate_type": candidate.candidate_type,
            "der_id": candidate.der_id,
            "sweep_run_id": candidate.sweep_run_id,
            "evidence_level": evidence_level,
            "expected_outcome": candidate.expected_outcome,
            "actual_outcome": candidate.actual_outcome,
            "resolution_trace_id": der.resolution_trace_id,
            "subjects": subjects,
            "context": context,
            "evaluator_lineage": evaluator_lineage,
            "known_limitations": list(candidate.missing_prerequisites),
            "authority": authority,
            "sealed_at": created_at,
        }
        manifest_digest = self._digest_object(manifest)
        bundle_id = f"urn:notary:evidence-bundle:{manifest_digest['value']}"
        candidate_ref = f"urn:notary:assurance-candidate:{candidate.id}"
        return EvidenceBundle(
            id=bundle_id,
            org_id=candidate.org_id,
            environment_id=candidate.environment_id,
            type="org.dep.evidence-bundle",
            subject_ref=candidate_ref,
            created_at=created_at,
            provenance={
                "epistemic_status": "derived",
                "provider_id": "urn:notary:proof-bridge",
                "collected_at": created_at,
            },
            integrity=manifest_digest,
            relationships=[
                {
                    "predicate": "urn:notary:relationship:derived-from",
                    "object_ref": f"urn:notary:decision-evidence-record:{candidate.der_id}",
                }
            ],
            extensions={"urn:notary:proof-bridge": manifest},
            manifest_digest=manifest_digest,
            subjects=subjects,
            declared_omissions=list(candidate.missing_prerequisites),
            custody_events=[
                {
                    "action": "sealed",
                    "actor": "proof_bridge",
                    "timestamp": created_at,
                    "authority": authority,
                }
            ],
            sealed_at=created_at,
        )

    def _record_incident_lineage(
        self,
        incident: Incident,
        candidate: AssuranceCandidate,
        der: Any,
        bundle_ref: str,
        authority: dict[str, Any],
        subjects: list[dict[str, Any]],
    ) -> None:
        lineage = {
            "candidate_id": candidate.id,
            "der_id": candidate.der_id,
            "sweep_run_id": candidate.sweep_run_id,
            "review_decision_id": authority["record"].get("id", "") if authority["kind"] == "review" else "",
            "promotion_delegation_id": authority["record"].get("id", "") if authority["kind"] == "delegation" else "",
            "evidence_bundle_ref": bundle_ref,
            "supporting_resource_digests": subjects,
            "resolution_trace_id": der.resolution_trace_id,
        }
        if incident.snapshot_summary.get("proof_bridge_lineage") != lineage:
            incident.snapshot_summary["proof_bridge_lineage"] = lineage
            incident._record_custody(
                "promoted_from_assurance_candidate",
                actor=authority["record"].get("actor", authority["record"].get("name", "proof_bridge")),
                detail=f"candidate={candidate.id}; bundle={bundle_ref}",
            )
            self._storage.update_incident(incident)

    def _resolve_authority(self, candidate: AssuranceCandidate, org_id: str) -> dict[str, Any] | None:
        reviews = [
            review
            for review in self._storage.list_review_decisions(candidate.id)
            if review.org_id == org_id and review.environment_id == candidate.environment_id
        ]
        superseded_ids = {review.superseded_decision_id for review in reviews if review.superseded_decision_id}
        active_reviews = [
            review
            for review in reviews
            if review.id not in superseded_ids and review.decision != "supersede" and self._period_is_active(review.effective_period)
        ]
        if active_reviews:
            latest = max(active_reviews, key=lambda review: (review.created_at, review.id))
            if latest.decision == "approve_incident":
                return {"kind": "review", "record": latest.to_dict()}
            return None

        delegation = self._check_delegation(candidate, org_id)
        if delegation is not None:
            return {"kind": "delegation", "record": delegation.to_dict()}
        return None

    def _check_delegation(self, candidate: AssuranceCandidate, org_id: str) -> PromotionDelegation | None:
        for delegation in self._storage.list_promotion_delegations(org_id):
            if (
                delegation.active
                and delegation.environment_id == candidate.environment_id
                and delegation.rule_type == "deterministic"
                and self._period_is_active(delegation.effective_period)
                and (not delegation.scope or delegation.scope == candidate.candidate_type)
                and (not delegation.conditions.get("evidence_level") or delegation.conditions["evidence_level"] == candidate.evidence_level)
                and (delegation.conditions.get("org_id", org_id) == org_id)
            ):
                required = set(delegation.conditions.get("required_prerequisites", []))
                if not required.intersection(candidate.missing_prerequisites):
                    return delegation
        return None

    @staticmethod
    def _period_is_active(period: str) -> bool:
        if not period:
            return True
        try:
            start_text, end_text = period.split("/", 1)
            now = datetime.now(timezone.utc)
            start = datetime.fromisoformat(start_text.replace("Z", "+00:00")) if start_text else None
            end = datetime.fromisoformat(end_text.replace("Z", "+00:00")) if end_text else None
            return (start is None or start <= now) and (end is None or now <= end)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _supporting_resource_ids(candidate: AssuranceCandidate, der: Any) -> list[str]:
        return list(dict.fromkeys([*candidate.supporting_resource_ids, *list(der.source_resource_ids if der else [])]))

    @staticmethod
    def _normalise_digest_algorithm(value: str) -> str:
        normalised = value.lower().replace("_", "-")
        return {"sha256": "sha-256", "sha384": "sha-384", "sha512": "sha-512"}.get(normalised, normalised)

    @staticmethod
    def _digest_object(value: Any) -> dict[str, str]:
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
        return {"algorithm": "sha-256", "value": hashlib.sha256(canonical).hexdigest()}

    @staticmethod
    def _public_replay_state(status: ReplayabilityStatus) -> str:
        return _PUBLIC_REPLAY_STATES.get(status, "missing_evidence")

    @staticmethod
    def _bridge_key(candidate: AssuranceCandidate) -> str:
        raw = "|".join([candidate.org_id, candidate.environment_id or "", candidate.id])
        return f"bridge-{hashlib.sha256(raw.encode()).hexdigest()}"

    @staticmethod
    def _verification_record_id(bridge_key: str) -> str:
        digest = hashlib.sha256(bridge_key.encode()).hexdigest()[:24]
        return f"vr-bridge-{digest}"

    @staticmethod
    def _incident_id(bridge_key: str) -> str:
        digest = hashlib.sha256(bridge_key.encode()).hexdigest()[:24]
        return f"inc-bridge-{digest}"

    @staticmethod
    def _verify_bundle_digest(bundle: dict[str, Any]) -> bool:
        """Verify that the bundle's manifest_digest matches its frozen manifest."""
        extension = bundle.get("extensions", {}).get("urn:notary:proof-bridge", {})
        if not extension:
            return False
        stored_digest = bundle.get("manifest_digest", {})
        if not stored_digest:
            return False
        # Recompute digest from the frozen manifest fields
        computed = ProofBridgeService._digest_object(extension)
        return computed["algorithm"] == stored_digest.get("algorithm") and computed["value"] == stored_digest.get("value")

    @staticmethod
    def _failure(code: str, prerequisite: str, next_action: str) -> dict[str, str]:
        return {"code": code, "prerequisite": prerequisite, "next_action": next_action}

    @classmethod
    def _blocked(cls, code: str, prerequisite: str, next_action: str) -> dict[str, Any]:
        failure = cls._failure(code, prerequisite, next_action)
        return {
            "eligible": False,
            "error_code": code,
            "reason": prerequisite,
            "next_actions": [next_action],
            "prerequisites": [prerequisite],
            "failures": [failure],
        }
