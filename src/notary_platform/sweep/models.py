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
