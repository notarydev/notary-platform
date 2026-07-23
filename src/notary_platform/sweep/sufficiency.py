"""Evidence Sufficiency Service — calculate E0-E4 deterministically.

Returns current level, satisfied predicates, failed predicates,
and exact requirements for the next level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from notary_platform.sweep.evaluators.base import (
    FrozenDecisionEvidenceRecord,
    ResolvedContext,
)


@dataclass
class SufficiencyResult:
    current_level: str  # E0, E1, E2, E3, E4
    satisfied: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    next_level_requirements: list[str] = field(default_factory=list)


class EvidenceSufficiencyService:
    """Calculate E0-E4 from deterministic predicates."""

    def calculate(
        self,
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
        has_replay_result: bool = False,
        has_verified_mutation: bool = False,
    ) -> SufficiencyResult:
        satisfied: list[str] = []
        failed: list[str] = []

        # E0: at least one attributable Observation
        e0_ok = bool(record.source_resource_ids) or bool(record.decision_identity)
        if e0_ok:
            satisfied.append("E0: attributable observation present")
        else:
            failed.append("E0: no attributable observation")

        # E1: E0 + at least one applicable Context Binding with no blocking identity ambiguity
        e1_ok = e0_ok and bool(record.context_binding_ids) and not context.conflicted_bindings
        if e1_ok:
            satisfied.append("E1: context binding applied without identity ambiguity")
        else:
            if not record.context_binding_ids:
                failed.append("E1: no applicable context binding")
            if context.conflicted_bindings:
                failed.append("E1: blocking identity ambiguity (conflicted bindings)")

        # E2: E1 + authoritative or independently corroborated context
        has_authoritative = bool(context.reasons.get("authoritative_context", False))
        has_corroborated = bool(context.reasons.get("corroborated_context", False))
        e2_ok = e1_ok and (has_authoritative or has_corroborated)
        if e2_ok:
            satisfied.append("E2: authoritative or corroborated context present")
        else:
            if not has_authoritative and not has_corroborated:
                failed.append("E2: no authoritative or corroborated context")

        # E3: E2 + integrity-verified sealed evidence + available replay path
        has_integrity = record.version >= 1
        has_replay_path = bool(record.resolution_trace_id) or has_replay_result
        e3_ok = e2_ok and has_integrity and has_replay_path
        if e3_ok:
            satisfied.append("E3: integrity-verified sealed evidence with replay path")
        else:
            if not has_integrity:
                failed.append("E3: evidence not integrity-verified (version < 1)")
            if not has_replay_path:
                failed.append("E3: no available replay path")

        # E4: E3 + successful original replay + verified mutation result
        e4_ok = e3_ok and has_replay_result and has_verified_mutation
        if e4_ok:
            satisfied.append("E4: successful replay with verified before/after fix")
        else:
            if not has_replay_result:
                failed.append("E4: no successful original replay")
            if not has_verified_mutation:
                failed.append("E4: no verified before/after fix result")

        current_level, next_level_reqs = self._determine_level(
            e0_ok, e1_ok, e2_ok, e3_ok, e4_ok,
        )

        return SufficiencyResult(
            current_level=current_level,
            satisfied=satisfied,
            failed=failed,
            next_level_requirements=next_level_reqs,
        )

    @staticmethod
    def _determine_level(
        e0: bool, e1: bool, e2: bool, e3: bool, e4: bool,
    ) -> tuple[str, list[str]]:
        if e4:
            return "E4", []
        if e3:
            return "E3", [
                "Run successful original replay",
                "Verify before/after fix result",
                "Retain evidence references",
            ]
        if e2:
            return "E2", [
                "Seal evidence with integrity verification",
                "Ensure available replay path exists",
            ]
        if e1:
            return "E1", [
                "Provide authoritative or corroborated context",
            ]
        if e0:
            return "E0", [
                "Provide at least one applicable Context Binding",
                "Resolve identity ambiguity (no conflicted bindings)",
            ]
        return "", [
            "Provide at least one attributable Observation",
        ]

    def format_report(self, result: SufficiencyResult) -> dict[str, Any]:
        return {
            "current_level": result.current_level,
            "satisfied": result.satisfied,
            "failed": result.failed,
            "next_level_requirements": result.next_level_requirements,
            "complete": result.current_level == "E4",
        }
