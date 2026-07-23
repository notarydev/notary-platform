"""Missing Evidence evaluator — compare observed resource/field coverage
to a versioned evidence requirement and enumerate missing, redacted,
stale, conflicted, or unverifiable items."""

from __future__ import annotations

from typing import Any

from notary_platform.sweep.evaluators.base import (
    BaseEvaluator,
    FrozenDecisionEvidenceRecord,
    ResolvedContext,
)
from notary_platform.sweep.models import AssessmentRecord


class MissingEvidenceEvaluator(BaseEvaluator):
    """Check whether the DER has sufficient resource and field coverage."""

    def evaluate(
        self,
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
        parameters: dict[str, Any],
    ) -> AssessmentRecord:
        missing = self.check_prerequisites(record, context)
        if missing:
            return self.skip_assessment(record, missing)

        required_fields: list[str] = parameters.get("required_fields", [])
        missing_items: list[str] = []
        redacted_items: list[str] = []
        stale_items: list[str] = []
        conflicted_items: list[str] = []
        unverifiable_items: list[str] = []

        if not record.source_resource_ids:
            missing_items.append("source_resources")
        for rid in record.source_resource_ids:
            if rid in context.redacted_artifacts:
                redacted_items.append(rid)
            if rid in context.stale_artifacts:
                stale_items.append(rid)
            if rid in context.missing_artifacts:
                missing_items.append(rid)
            if rid in context.conflicted_bindings:
                conflicted_items.append(rid)

        if required_fields:
            for field in required_fields:
                if field not in str(record):  # crude placeholder — real impl inspects resources
                    missing_items.append(field)

        details: dict[str, Any] = {
            "observed_resources": list(record.source_resource_ids),
            "missing": missing_items,
            "redacted": redacted_items,
            "stale": stale_items,
            "conflicted": conflicted_items,
            "unverifiable": unverifiable_items,
        }

        if missing_items or redacted_items or stale_items or conflicted_items:
            finding_type = "missing_evidence"
            summary = "Evidence gaps found"
            if missing_items:
                summary += f": {len(missing_items)} missing"
            if redacted_items:
                summary += f", {len(redacted_items)} redacted"
            if stale_items:
                summary += f", {len(stale_items)} stale"
            if conflicted_items:
                summary += f", {len(conflicted_items)} conflicted"
        else:
            finding_type = ""
            summary = "All required evidence present"
            details["status"] = "sufficient"

        return AssessmentRecord(
            org_id=record.org_id,
            run_id="",
            evaluator_id=self.contract.id,
            evaluator_version=self.contract.version,
            der_id=record.id,
            finding_type=finding_type,
            status="assessed",
            summary=summary,
            details=details,
        )
