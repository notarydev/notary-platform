"""Candidate assembly and review services for WP-080."""

from __future__ import annotations

from typing import Any

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
from notary_platform.sweep.sufficiency import EvidenceSufficiencyService


class CandidateAssembler:
    """Assemble assessments into AssuranceCandidates."""

    def __init__(self, storage: Any) -> None:
        self._storage = storage
        self._sufficiency = EvidenceSufficiencyService()

    def assemble(
        self,
        assessments: list[AssessmentRecord],
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
        sweep_run_id: str,
        environment_id: str = "",
    ) -> list[AssuranceCandidate]:
        sufficiency = self._sufficiency.calculate(record, context)
        candidates: list[AssuranceCandidate] = []

        for assessment in assessments:
            if assessment.status != "assessed" or not assessment.finding_type:
                continue

            candidate = AssuranceCandidate(
                org_id=record.org_id,
                environment_id=environment_id,
                der_id=record.id,
                sweep_run_id=sweep_run_id,
                candidate_type=assessment.finding_type,
                assessment_ids=[assessment.id],
                supporting_resource_ids=list(record.source_resource_ids),
                context_binding_ids=list(record.context_binding_ids),
                resolution_trace_id=record.resolution_trace_id,
                evidence_level=sufficiency.current_level,
                severity=self._assess_severity(assessment),
                lifecycle_state="reviewable" if sufficiency.current_level in ("E2", "E3", "E4") else "needs_context",
                business_summary=assessment.summary,
                actual_outcome=assessment.details.get("actual_outcome", ""),
                expected_outcome=assessment.details.get("expected_outcome", ""),
            )
            self._storage.create_assurance_candidate(candidate)
            candidates.append(candidate)

        return candidates

    @staticmethod
    def _assess_severity(assessment: AssessmentRecord) -> str:
        if "missing" in assessment.finding_type and assessment.details.get("missing"):
            return "high"
        if assessment.finding_type == "expected_outcome_mismatch":
            return "high"
        if assessment.finding_type == "replayability_failure":
            return "medium"
        return "low"


class CandidateReviewService:
    """Handle candidate review lifecycle."""

    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def record_review(self, candidate_id: str, decision: ReviewDecision) -> ReviewDecision | None:
        candidate = self._storage.get_assurance_candidate(candidate_id)
        if candidate is None or candidate.org_id != decision.org_id:
            return None
        if not decision.actor or not decision.role or not decision.decision:
            return None
        if decision.decision in {"approve_incident", "dismiss", "accept_risk", "suppress"} and not decision.basis:
            return None

        created = self._storage.create_review_decision(decision)

        lifecycle_map: dict[str, str] = {
            "approve_incident": "approved_incident",
            "dismiss": "dismissed",
            "accept_risk": "accepted_risk",
            "suppress": "suppressed",
            "instrument_next": "instrument_next",
            "request_context": "needs_context",
        }
        new_state = lifecycle_map.get(decision.decision)
        if new_state and new_state != candidate.lifecycle_state:
            candidate.lifecycle_state = new_state
            self._storage.update_assurance_candidate(candidate)

        return created

    def get_reviews(self, candidate_id: str) -> list[ReviewDecision]:
        return self._storage.list_review_decisions(candidate_id)

    def create_suppression(self, rule: SuppressionRule) -> SuppressionRule:
        return self._storage.create_suppression_rule(rule)

    def list_suppressions(self, org_id: str) -> list[SuppressionRule]:
        return self._storage.list_suppression_rules(org_id)

    def create_delegation(self, delegation: PromotionDelegation) -> PromotionDelegation:
        return self._storage.create_promotion_delegation(delegation)

    def list_delegations(self, org_id: str) -> list[PromotionDelegation]:
        return self._storage.list_promotion_delegations(org_id)

    def check_delegation(
        self,
        candidate: AssuranceCandidate,
        org_id: str,
    ) -> PromotionDelegation | None:
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
