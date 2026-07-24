"""Expected Outcome Mismatch evaluator — compare observed actual outcome
to customer-confirmed or authoritative expected outcome applicable at
decision time."""

from __future__ import annotations

from typing import Any

from notary_platform.sweep.evaluators.base import (
    BaseEvaluator,
    FrozenDecisionEvidenceRecord,
    ResolvedContext,
)
from notary_platform.sweep.models import AssessmentRecord


class ExpectedOutcomeMismatchEvaluator(BaseEvaluator):
    """Check whether the actual outcome matches the expected outcome."""

    def evaluate(
        self,
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
        parameters: dict[str, Any],
    ) -> AssessmentRecord:
        missing = self.check_prerequisites(record, context)
        if missing:
            return self.skip_assessment(record, missing)

        # Cannot run on inferred/unconfirmed identity
        if record.identity_method in ("inferred", "similarity"):
            return AssessmentRecord(
                org_id=record.org_id,
                run_id="",
                evaluator_id=self.contract.id,
                evaluator_version=self.contract.version,
                der_id=record.id,
                finding_type="",
                status="skipped",
                summary="Expected-outcome mismatch cannot run on inferred or unconfirmed identity",
                details={
                    "identity_method": record.identity_method,
                    "reason": "requires confirmed identity for outcome comparison",
                },
            )

        actual_outcome = parameters.get("actual_outcome", "")
        expected_outcome = parameters.get("expected_outcome", "")
        comparison_rule = parameters.get("comparison_rule", "exact")

        if not actual_outcome or not expected_outcome:
            return AssessmentRecord(
                org_id=record.org_id,
                run_id="",
                evaluator_id=self.contract.id,
                evaluator_version=self.contract.version,
                der_id=record.id,
                finding_type="missing_evidence",
                status="assessed",
                summary="Missing outcome data for comparison",
                details={
                    "has_actual": bool(actual_outcome),
                    "has_expected": bool(expected_outcome),
                },
            )

        mismatch = self._compare(actual_outcome, expected_outcome, comparison_rule)

        details: dict[str, Any] = {
            "actual_outcome": actual_outcome,
            "expected_outcome": expected_outcome,
            "comparison_rule": comparison_rule,
            "mismatch": mismatch,
            "identity_method": record.identity_method,
        }

        if mismatch:
            return AssessmentRecord(
                org_id=record.org_id,
                run_id="",
                evaluator_id=self.contract.id,
                evaluator_version=self.contract.version,
                der_id=record.id,
                finding_type="expected_outcome_mismatch",
                status="assessed",
                summary="Actual outcome does not match expected outcome",
                details=details,
            )

        details["status"] = "matched"
        return AssessmentRecord(
            org_id=record.org_id,
            run_id="",
            evaluator_id=self.contract.id,
            evaluator_version=self.contract.version,
            der_id=record.id,
            finding_type="",
            status="assessed",
            summary="Actual outcome matches expected outcome",
            details=details,
        )

    @staticmethod
    def _compare(actual: str, expected: str, rule: str) -> bool:
        if rule == "exact":
            return actual.strip() != expected.strip()
        if rule == "case_insensitive":
            return actual.strip().lower() != expected.strip().lower()
        if rule == "numeric":
            try:
                return abs(float(actual) - float(expected)) > 0.001
            except (ValueError, TypeError):
                return True
        return actual != expected
