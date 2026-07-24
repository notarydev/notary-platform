"""Domain models for Sweep runtime — definitions, runs, evaluations, and contracts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

# ── Evaluator Contract ──


@dataclass
class EvaluatorContractRecord:
    id: str = ""
    org_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    method_class: str = "deterministic"  # deterministic | advisory
    trust_class: str = "authoritative"  # authoritative | advisory
    required_prerequisites: list[str] = field(default_factory=list)
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"eval-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "method_class": self.method_class,
            "trust_class": self.trust_class,
            "required_prerequisites": list(self.required_prerequisites),
            "parameters_schema": dict(self.parameters_schema),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvaluatorContractRecord:
        return cls(
            id=d.get("id", f"eval-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            name=d.get("name", ""),
            version=d.get("version", "1.0.0"),
            description=d.get("description", ""),
            method_class=d.get("method_class", "deterministic"),
            trust_class=d.get("trust_class", "authoritative"),
            required_prerequisites=list(d.get("required_prerequisites", [])),
            parameters_schema=d.get("parameters_schema", {}),
            created_at=d.get("created_at", ""),
        )


# ── Sweep Definition ──


@dataclass
class SweepDefinition:
    id: str = ""
    org_id: str = ""
    name: str = ""
    description: str = ""
    environment_id: str = ""
    source_ids: list[str] = field(default_factory=list)
    evaluator_ids: list[str] = field(default_factory=list)
    mapping_version_ids: list[str] = field(default_factory=list)
    suppressions: list[str] = field(default_factory=list)
    budget_record_limit: int = 10000
    budget_evaluator_limit: int = 50
    budget_timeout_seconds: int = 300
    schedule: str = ""  # cron expression or empty for manual
    enabled: bool = True
    version: int = 1
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"sd-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "name": self.name,
            "description": self.description,
            "environment_id": self.environment_id,
            "source_ids": list(self.source_ids),
            "evaluator_ids": list(self.evaluator_ids),
            "mapping_version_ids": list(self.mapping_version_ids),
            "suppressions": list(self.suppressions),
            "budget_record_limit": self.budget_record_limit,
            "budget_evaluator_limit": self.budget_evaluator_limit,
            "budget_timeout_seconds": self.budget_timeout_seconds,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "version": self.version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SweepDefinition:
        return cls(
            id=d.get("id", f"sd-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            environment_id=d.get("environment_id", ""),
            source_ids=list(d.get("source_ids", [])),
            evaluator_ids=list(d.get("evaluator_ids", [])),
            mapping_version_ids=list(d.get("mapping_version_ids", [])),
            suppressions=list(d.get("suppressions", [])),
            budget_record_limit=d.get("budget_record_limit", 10000),
            budget_evaluator_limit=d.get("budget_evaluator_limit", 50),
            budget_timeout_seconds=d.get("budget_timeout_seconds", 300),
            schedule=d.get("schedule", ""),
            enabled=d.get("enabled", True),
            version=d.get("version", 1),
            created_at=d.get("created_at", ""),
        )


# ── Sweep Run ──


@dataclass
class SweepRun:
    id: str = ""
    org_id: str = ""
    environment_id: str = ""
    definition_id: str = ""
    status: str = "queued"  # queued, profiling, resolving, evaluating, assembling, completed, completed_with_errors, failed, cancelled
    manifest_ref: str = ""
    source_cursors: dict[str, str] = field(default_factory=dict)
    record_count: int = 0
    evaluator_count: int = 0
    executed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    suppressed_count: int = 0
    candidate_count: int = 0
    error_message: str = ""
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"sr-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "definition_id": self.definition_id,
            "status": self.status,
            "manifest_ref": self.manifest_ref,
            "source_cursors": dict(self.source_cursors),
            "record_count": self.record_count,
            "evaluator_count": self.evaluator_count,
            "executed_count": self.executed_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "suppressed_count": self.suppressed_count,
            "candidate_count": self.candidate_count,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SweepRun:
        return cls(
            id=d.get("id", f"sr-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            environment_id=d.get("environment_id", ""),
            definition_id=d.get("definition_id", ""),
            status=d.get("status", "queued"),
            manifest_ref=d.get("manifest_ref", ""),
            source_cursors=d.get("source_cursors", {}),
            record_count=d.get("record_count", 0),
            evaluator_count=d.get("evaluator_count", 0),
            executed_count=d.get("executed_count", 0),
            skipped_count=d.get("skipped_count", 0),
            failed_count=d.get("failed_count", 0),
            suppressed_count=d.get("suppressed_count", 0),
            candidate_count=d.get("candidate_count", 0),
            error_message=d.get("error_message", ""),
            created_at=d.get("created_at", ""),
            started_at=d.get("started_at", ""),
            completed_at=d.get("completed_at", ""),
        )


# ── Evaluation Execution ──


@dataclass
class EvaluationExecution:
    id: str = ""
    org_id: str = ""
    run_id: str = ""
    evaluator_id: str = ""
    der_id: str = ""
    status: str = "planned"  # planned, executed, skipped, failed, suppressed
    output: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    error_message: str = ""
    skip_reason: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"ee-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "run_id": self.run_id,
            "evaluator_id": self.evaluator_id,
            "der_id": self.der_id,
            "status": self.status,
            "output": dict(self.output),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "skip_reason": self.skip_reason,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvaluationExecution:
        return cls(
            id=d.get("id", f"ee-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            run_id=d.get("run_id", ""),
            evaluator_id=d.get("evaluator_id", ""),
            der_id=d.get("der_id", ""),
            status=d.get("status", "planned"),
            output=d.get("output", {}),
            error_code=d.get("error_code", ""),
            error_message=d.get("error_message", ""),
            skip_reason=d.get("skip_reason", ""),
            created_at=d.get("created_at", ""),
        )


# ── Assessment Record (moved from WP-070, shared type) ──


@dataclass
class AssessmentRecord:
    id: str = ""
    org_id: str = ""
    run_id: str = ""
    evaluator_id: str = ""
    evaluator_version: str = ""
    der_id: str = ""
    finding_type: str = ""  # missing_evidence, expected_outcome_mismatch, replayability_failure
    status: str = "assessed"  # assessed, skipped, failed, suppressed
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    evidence_level: str = ""  # E0, E1, E2, E3, E4 or empty
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"ar-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "run_id": self.run_id,
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
            "der_id": self.der_id,
            "finding_type": self.finding_type,
            "status": self.status,
            "summary": self.summary,
            "details": dict(self.details),
            "evidence_level": self.evidence_level,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AssessmentRecord:
        return cls(
            id=d.get("id", f"ar-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            run_id=d.get("run_id", ""),
            evaluator_id=d.get("evaluator_id", ""),
            evaluator_version=d.get("evaluator_version", ""),
            der_id=d.get("der_id", ""),
            finding_type=d.get("finding_type", ""),
            status=d.get("status", "assessed"),
            summary=d.get("summary", ""),
            details=d.get("details", {}),
            evidence_level=d.get("evidence_level", ""),
            created_at=d.get("created_at", ""),
        )


class Evaluator(Protocol):
    """Interface for evaluator implementations (WP-070)."""

    contract: EvaluatorContractRecord

    def evaluate(
        self,
        record: Any,  # FrozenDecisionEvidenceRecord
        context: Any,  # ResolvedContext
        parameters: dict[str, Any],
    ) -> AssessmentRecord: ...


# ── WP-080: Assurance Candidate ──


@dataclass
class AssuranceCandidate:
    id: str = ""
    org_id: str = ""
    environment_id: str = ""
    der_id: str = ""
    sweep_run_id: str = ""
    candidate_type: str = ""  # missing_evidence, expected_outcome_mismatch, replayability_failure
    assessment_ids: list[str] = field(default_factory=list)
    supporting_resource_ids: list[str] = field(default_factory=list)
    context_binding_ids: list[str] = field(default_factory=list)
    resolution_trace_id: str = ""
    missing_prerequisites: list[str] = field(default_factory=list)
    evidence_level: str = ""  # E0, E1, E2, E3, E4
    severity: str = "medium"  # info, low, medium, high, critical
    lifecycle_state: str = "needs_context"  # needs_context, reviewable, approved_incident, dismissed, accepted_risk, suppressed, instrument_next
    business_summary: str = ""
    actual_outcome: str = ""
    expected_outcome: str = ""
    priority_basis: str = ""
    impact_hypothesis: str = ""
    cluster_ref: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"ac-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "der_id": self.der_id,
            "sweep_run_id": self.sweep_run_id,
            "candidate_type": self.candidate_type,
            "assessment_ids": list(self.assessment_ids),
            "supporting_resource_ids": list(self.supporting_resource_ids),
            "context_binding_ids": list(self.context_binding_ids),
            "resolution_trace_id": self.resolution_trace_id,
            "missing_prerequisites": list(self.missing_prerequisites),
            "evidence_level": self.evidence_level,
            "severity": self.severity,
            "lifecycle_state": self.lifecycle_state,
            "business_summary": self.business_summary,
            "actual_outcome": self.actual_outcome,
            "expected_outcome": self.expected_outcome,
            "priority_basis": self.priority_basis,
            "impact_hypothesis": self.impact_hypothesis,
            "cluster_ref": self.cluster_ref,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AssuranceCandidate:
        return cls(
            id=d.get("id", f"ac-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            environment_id=d.get("environment_id", ""),
            der_id=d.get("der_id", ""),
            sweep_run_id=d.get("sweep_run_id", ""),
            candidate_type=d.get("candidate_type", ""),
            assessment_ids=list(d.get("assessment_ids", [])),
            supporting_resource_ids=list(d.get("supporting_resource_ids", [])),
            context_binding_ids=list(d.get("context_binding_ids", [])),
            resolution_trace_id=d.get("resolution_trace_id", ""),
            missing_prerequisites=list(d.get("missing_prerequisites", [])),
            evidence_level=d.get("evidence_level", ""),
            severity=d.get("severity", "medium"),
            lifecycle_state=d.get("lifecycle_state", "needs_context"),
            business_summary=d.get("business_summary", ""),
            actual_outcome=d.get("actual_outcome", ""),
            expected_outcome=d.get("expected_outcome", ""),
            priority_basis=d.get("priority_basis", ""),
            impact_hypothesis=d.get("impact_hypothesis", ""),
            cluster_ref=d.get("cluster_ref", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class ReviewDecision:
    id: str = ""
    candidate_id: str = ""
    org_id: str = ""
    environment_id: str = ""
    actor: str = ""
    role: str = ""
    decision: str = ""  # approve_incident, dismiss, request_context, accept_risk, suppress, instrument_next, supersede
    basis: str = ""
    scope: str = ""
    effective_period: str = ""
    superseded_decision_id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"rd-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "actor": self.actor,
            "role": self.role,
            "decision": self.decision,
            "basis": self.basis,
            "scope": self.scope,
            "effective_period": self.effective_period,
            "superseded_decision_id": self.superseded_decision_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReviewDecision:
        return cls(
            id=d.get("id", f"rd-{uuid.uuid4().hex[:12]}"),
            candidate_id=d.get("candidate_id", ""),
            org_id=d.get("org_id", ""),
            environment_id=d.get("environment_id", ""),
            actor=d.get("actor", ""),
            role=d.get("role", ""),
            decision=d.get("decision", ""),
            basis=d.get("basis", ""),
            scope=d.get("scope", ""),
            effective_period=d.get("effective_period", ""),
            superseded_decision_id=d.get("superseded_decision_id", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class SuppressionRule:
    id: str = ""
    org_id: str = ""
    scope: str = ""  # der_id, evaluator_id, candidate_type, source_id
    scope_value: str = ""
    reason: str = ""
    created_by: str = ""
    active: bool = True
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"sr-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "scope": self.scope,
            "scope_value": self.scope_value,
            "reason": self.reason,
            "created_by": self.created_by,
            "active": self.active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SuppressionRule:
        return cls(
            id=d.get("id", f"sr-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            scope=d.get("scope", ""),
            scope_value=d.get("scope_value", ""),
            reason=d.get("reason", ""),
            created_by=d.get("created_by", ""),
            active=d.get("active", True),
            created_at=d.get("created_at", ""),
        )


@dataclass
class PromotionDelegation:
    id: str = ""
    org_id: str = ""
    environment_id: str = ""
    created_by: str = ""
    name: str = ""
    version: str = "1.0.0"
    rule_type: str = ""  # deterministic, probabilistic
    conditions: dict[str, Any] = field(default_factory=dict)
    scope: str = ""
    effective_period: str = ""
    active: bool = True
    revoked_by: str = ""
    revoked_at: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"pd-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "created_by": self.created_by,
            "name": self.name,
            "version": self.version,
            "rule_type": self.rule_type,
            "conditions": dict(self.conditions),
            "scope": self.scope,
            "effective_period": self.effective_period,
            "active": self.active,
            "revoked_by": self.revoked_by,
            "revoked_at": self.revoked_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromotionDelegation:
        return cls(
            id=d.get("id", f"pd-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            environment_id=d.get("environment_id", ""),
            created_by=d.get("created_by", ""),
            name=d.get("name", ""),
            version=d.get("version", "1.0.0"),
            rule_type=d.get("rule_type", ""),
            conditions=d.get("conditions", {}),
            scope=d.get("scope", ""),
            effective_period=d.get("effective_period", ""),
            active=d.get("active", True),
            revoked_by=d.get("revoked_by", ""),
            revoked_at=d.get("revoked_at", ""),
            created_at=d.get("created_at", ""),
        )
