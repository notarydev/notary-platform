"""Replayability Failure evaluator — identify missing cassette calls,
mutable dependencies, unsupported tools, missing seed/configuration,
unavailable runner, and required instrumentation action."""

from __future__ import annotations

from typing import Any

from notary_platform.sweep.evaluators.base import (
    BaseEvaluator,
    FrozenDecisionEvidenceRecord,
    ResolvedContext,
)
from notary_platform.sweep.models import AssessmentRecord


class ReplayabilityFailureEvaluator(BaseEvaluator):
    """Check replayability predicates for a DER."""

    def evaluate(
        self,
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
        parameters: dict[str, Any],
    ) -> AssessmentRecord:
        missing = self.check_prerequisites(record, context)
        if missing:
            return self.skip_assessment(record, missing)

        findings: list[str] = []
        actions: list[str] = []

        # Check cassette availability
        cassette_missing = parameters.get("cassette_missing", False)
        if cassette_missing:
            findings.append("missing_cassette_calls")
            actions.append("Capture API calls with the Notary SDK cassette recorder")

        # Check mutable dependencies
        mutable_deps = parameters.get("mutable_dependencies", [])
        if mutable_deps:
            findings.append("mutable_dependencies")
            actions.append("Freeze or sandbox dependencies: " + ", ".join(mutable_deps))

        # Check unsupported tools
        unsupported_tools = parameters.get("unsupported_tools", [])
        if unsupported_tools:
            findings.append("unsupported_tools")
            actions.append("Replace unsupported tools: " + ", ".join(unsupported_tools))

        # Check seed/configuration
        missing_seed = parameters.get("missing_seed", False)
        if missing_seed:
            findings.append("missing_seed_or_configuration")
            actions.append("Provide seed data and configuration snapshot")

        # Check runner availability
        runner_available = parameters.get("runner_available", True)
        if not runner_available:
            findings.append("runner_unavailable")
            actions.append("Deploy or configure the Notary replay runner")

        # Check instrumentation
        needs_instrumentation = parameters.get("needs_instrumentation", False)
        if needs_instrumentation:
            findings.append("required_instrumentation")
            actions.append("Instrument the application with the Notary SDK")

        # Evidence-level based checks
        if record.version < 1:
            findings.append("no_sealed_evidence")
            actions.append("Seal evidence with integrity verification")

        if context.missing_artifacts:
            findings.append("missing_context_artifacts")
            actions.append("Provide missing context artifacts: " + ", ".join(context.missing_artifacts))

        details: dict[str, Any] = {
            "findings": findings,
            "recommended_actions": actions,
            "source_resource_count": len(record.source_resource_ids),
            "context_binding_count": len(record.context_binding_ids),
        }

        if findings:
            return AssessmentRecord(
                org_id=record.org_id,
                run_id="",
                evaluator_id=self.contract.id,
                evaluator_version=self.contract.version,
                der_id=record.id,
                finding_type="replayability_failure",
                status="assessed",
                summary=f"Replayability blocked: {len(findings)} issue(s)",
                details=details,
            )

        details["status"] = "replayable"
        return AssessmentRecord(
            org_id=record.org_id,
            run_id="",
            evaluator_id=self.contract.id,
            evaluator_version=self.contract.version,
            der_id=record.id,
            finding_type="",
            status="assessed",
            summary="Decision is replayable",
            details=details,
        )
