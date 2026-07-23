"""Base evaluator types for WP-070.

FrozenDecisionEvidenceRecord and ResolvedContext are immutable views
passed into evaluators so that implementations cannot mutate records,
fetch source data, call production systems, or promote candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from notary_platform.sweep.models import AssessmentRecord, EvaluatorContractRecord


@dataclass(frozen=True)
class FrozenDecisionEvidenceRecord:
    id: str
    org_id: str
    decision_identity: str
    identity_method: str
    source_resource_ids: tuple[str, ...]
    context_binding_ids: tuple[str, ...]
    link_assertion_ids: tuple[str, ...]
    resolution_trace_id: str
    enriched: bool
    version: int
    created_at: str


@dataclass(frozen=True)
class ResolvedContext:
    binding_ids: tuple[str, ...]
    included_artifacts: tuple[str, ...]
    excluded_artifacts: tuple[str, ...]
    superseded_bindings: tuple[str, ...]
    conflicted_bindings: tuple[str, ...]
    missing_artifacts: tuple[str, ...]
    stale_artifacts: tuple[str, ...]
    redacted_artifacts: tuple[str, ...]
    reasons: dict[str, Any] = field(default_factory=dict)


class Evaluator(Protocol):
    contract: EvaluatorContractRecord

    def evaluate(
        self,
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
        parameters: dict[str, Any],
    ) -> AssessmentRecord: ...


class BaseEvaluator:
    contract: EvaluatorContractRecord

    def __init__(self, contract: EvaluatorContractRecord) -> None:
        self.contract = contract

    def skip_assessment(
        self,
        record: FrozenDecisionEvidenceRecord,
        missing: list[str],
    ) -> AssessmentRecord:
        return AssessmentRecord(
            org_id=record.org_id,
            run_id="",
            evaluator_id=self.contract.id,
            evaluator_version=self.contract.version,
            der_id=record.id,
            finding_type="",
            status="skipped",
            summary=f"Missing prerequisites: {', '.join(missing)}",
            details={"missing_prerequisites": missing},
        )

    def check_prerequisites(
        self,
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
    ) -> list[str]:
        missing: list[str] = []
        for prereq in self.contract.required_prerequisites:
            if prereq == "context_resolved" and not record.resolution_trace_id:
                missing.append("context_resolved")
            elif prereq == "context_bindings" and not record.context_binding_ids:
                missing.append("context_bindings")
            elif prereq == "source_resources" and not record.source_resource_ids:
                missing.append("source_resources")
            elif prereq == "link_assertions" and not record.link_assertion_ids:
                missing.append("link_assertions")
        return missing
