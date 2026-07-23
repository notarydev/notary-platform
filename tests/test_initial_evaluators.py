"""WP-070: Evaluator tests — missing_evidence, expected_outcome_mismatch, replayability_failure."""

from __future__ import annotations

from notary_platform.sweep.evaluators.base import (
    BaseEvaluator,
    FrozenDecisionEvidenceRecord,
    ResolvedContext,
)
from notary_platform.sweep.evaluators.expected_outcome import ExpectedOutcomeMismatchEvaluator
from notary_platform.sweep.evaluators.missing_evidence import MissingEvidenceEvaluator
from notary_platform.sweep.evaluators.replayability import ReplayabilityFailureEvaluator
from notary_platform.sweep.models import EvaluatorContractRecord


def _make_record(
    source_ids: tuple[str, ...] = ("res-1",),
    binding_ids: tuple[str, ...] = ("cb-1",),
    resolution_trace_id: str = "rt-1",
    identity_method: str = "exact_id",
) -> FrozenDecisionEvidenceRecord:
    return FrozenDecisionEvidenceRecord(
        id="der-1",
        org_id="test-org",
        decision_identity="res-1",
        identity_method=identity_method,
        source_resource_ids=source_ids,
        context_binding_ids=binding_ids,
        link_assertion_ids=(),
        resolution_trace_id=resolution_trace_id,
        enriched=False,
        version=1,
        created_at="2026-07-01T12:00:00Z",
    )


def _make_context(
    conflicted: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
    stale: tuple[str, ...] = (),
    redacted: tuple[str, ...] = (),
    authoritative: bool = False,
    corroborated: bool = False,
) -> ResolvedContext:
    return ResolvedContext(
        binding_ids=("cb-1",),
        included_artifacts=("res-1",),
        excluded_artifacts=(),
        superseded_bindings=(),
        conflicted_bindings=conflicted,
        missing_artifacts=missing,
        stale_artifacts=stale,
        redacted_artifacts=redacted,
        reasons={
            "authoritative_context": authoritative,
            "corroborated_context": corroborated,
        },
    )


# ── Missing Evidence Evaluator ──


class TestMissingEvidenceEvaluator:
    def test_all_evidence_present(self) -> None:
        contract = EvaluatorContractRecord(id="eval-001", name="missing-evidence", required_prerequisites=["context_resolved"])
        evaluator = MissingEvidenceEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {})
        assert result.status == "assessed"
        assert result.finding_type == ""
        assert result.details.get("status") == "sufficient"

    def test_missing_prerequisites_skips(self) -> None:
        contract = EvaluatorContractRecord(id="eval-001", name="missing-evidence", required_prerequisites=["context_resolved", "context_bindings"])
        evaluator = MissingEvidenceEvaluator(contract)
        record = _make_record(binding_ids=(), resolution_trace_id="")
        context = _make_context()
        result = evaluator.evaluate(record, context, {})
        assert result.status == "skipped"
        assert "Missing prerequisites" in result.summary

    def test_detects_missing_resources(self) -> None:
        contract = EvaluatorContractRecord(id="eval-001", name="missing-evidence")
        evaluator = MissingEvidenceEvaluator(contract)
        record = _make_record(source_ids=())
        context = _make_context()
        result = evaluator.evaluate(record, context, {})
        assert result.status == "assessed"
        assert result.finding_type == "missing_evidence"
        assert "source_resources" in result.details["missing"]

    def test_detects_redacted_evidence(self) -> None:
        contract = EvaluatorContractRecord(id="eval-001", name="missing-evidence")
        evaluator = MissingEvidenceEvaluator(contract)
        record = _make_record()
        context = _make_context(redacted=("res-1",))
        result = evaluator.evaluate(record, context, {})
        assert result.status == "assessed"
        assert result.finding_type == "missing_evidence"
        assert "res-1" in result.details["redacted"]

    def test_detects_stale_evidence(self) -> None:
        contract = EvaluatorContractRecord(id="eval-001", name="missing-evidence")
        evaluator = MissingEvidenceEvaluator(contract)
        record = _make_record()
        context = _make_context(stale=("res-1",))
        result = evaluator.evaluate(record, context, {})
        assert result.status == "assessed"
        assert result.finding_type == "missing_evidence"
        assert "res-1" in result.details["stale"]

    def test_detects_conflicted_evidence(self) -> None:
        contract = EvaluatorContractRecord(id="eval-001", name="missing-evidence")
        evaluator = MissingEvidenceEvaluator(contract)
        record = _make_record()
        context = _make_context(conflicted=("res-1",))
        result = evaluator.evaluate(record, context, {})
        assert result.status == "assessed"
        assert result.finding_type == "missing_evidence"
        assert "res-1" in result.details["conflicted"]


# ── Expected Outcome Mismatch Evaluator ──


class TestExpectedOutcomeMismatchEvaluator:
    def test_outcome_matches(self) -> None:
        contract = EvaluatorContractRecord(id="eval-002", name="outcome-check")
        evaluator = ExpectedOutcomeMismatchEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "actual_outcome": "approved",
            "expected_outcome": "approved",
        })
        assert result.status == "assessed"
        assert result.finding_type == ""
        assert result.details.get("status") == "matched"

    def test_outcome_mismatch_detected(self) -> None:
        contract = EvaluatorContractRecord(id="eval-002", name="outcome-check")
        evaluator = ExpectedOutcomeMismatchEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "actual_outcome": "denied",
            "expected_outcome": "approved",
        })
        assert result.status == "assessed"
        assert result.finding_type == "expected_outcome_mismatch"
        assert result.details["mismatch"] is True

    def test_skips_on_inferred_identity(self) -> None:
        contract = EvaluatorContractRecord(id="eval-002", name="outcome-check")
        evaluator = ExpectedOutcomeMismatchEvaluator(contract)
        record = _make_record(identity_method="inferred")
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "actual_outcome": "approved",
            "expected_outcome": "approved",
        })
        assert result.status == "skipped"
        assert "inferred" in result.summary

    def test_skips_on_similarity_identity(self) -> None:
        contract = EvaluatorContractRecord(id="eval-002", name="outcome-check")
        evaluator = ExpectedOutcomeMismatchEvaluator(contract)
        record = _make_record(identity_method="similarity")
        context = _make_context()
        result = evaluator.evaluate(record, context, {})
        assert result.status == "skipped"

    def test_missing_outcome_data(self) -> None:
        contract = EvaluatorContractRecord(id="eval-002", name="outcome-check")
        evaluator = ExpectedOutcomeMismatchEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {})
        assert result.status == "assessed"
        assert result.finding_type == "missing_evidence"
        assert result.details["has_actual"] is False

    def test_case_insensitive_comparison(self) -> None:
        contract = EvaluatorContractRecord(id="eval-002", name="outcome-check")
        evaluator = ExpectedOutcomeMismatchEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "actual_outcome": "APPROVED",
            "expected_outcome": "approved",
            "comparison_rule": "case_insensitive",
        })
        assert result.finding_type == ""

    def test_missing_prerequisites_skips(self) -> None:
        contract = EvaluatorContractRecord(id="eval-002", name="outcome-check", required_prerequisites=["source_resources"])
        evaluator = ExpectedOutcomeMismatchEvaluator(contract)
        record = _make_record(source_ids=())
        context = _make_context()
        result = evaluator.evaluate(record, context, {})
        assert result.status == "skipped"
        assert "Missing prerequisites" in result.summary


# ── Replayability Failure Evaluator ──


class TestReplayabilityFailureEvaluator:
    def test_replayable_when_all_conditions_met(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "cassette_missing": False,
            "runner_available": True,
            "missing_seed": False,
            "needs_instrumentation": False,
        })
        assert result.status == "assessed"
        assert result.finding_type == ""
        assert result.details.get("status") == "replayable"

    def test_detects_missing_cassette(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "cassette_missing": True,
        })
        assert result.status == "assessed"
        assert result.finding_type == "replayability_failure"
        assert "missing_cassette_calls" in result.details["findings"]

    def test_detects_mutable_dependencies(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "mutable_dependencies": ["database", "external-api"],
        })
        assert result.status == "assessed"
        assert "mutable_dependencies" in result.details["findings"]
        assert len(result.details["recommended_actions"]) > 0

    def test_detects_unsupported_tools(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "unsupported_tools": ["legacy-simulator"],
        })
        assert "unsupported_tools" in result.details["findings"]

    def test_detects_missing_seed(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "missing_seed": True,
        })
        assert "missing_seed_or_configuration" in result.details["findings"]

    def test_detects_runner_unavailable(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "runner_available": False,
        })
        assert "runner_unavailable" in result.details["findings"]

    def test_detects_needs_instrumentation(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "needs_instrumentation": True,
        })
        assert "required_instrumentation" in result.details["findings"]

    def test_detects_missing_context_artifacts(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context(missing=("res-missing",))
        result = evaluator.evaluate(record, context, {})
        assert "missing_context_artifacts" in result.details["findings"]

    def test_identifies_concrete_action(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check")
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record()
        context = _make_context()
        result = evaluator.evaluate(record, context, {
            "cassette_missing": True,
            "runner_available": False,
        })
        actions = result.details["recommended_actions"]
        assert any("Capture API calls" in a for a in actions)
        assert any("Deploy" in a and "replay runner" in a for a in actions)

    def test_missing_prerequisites_skips(self) -> None:
        contract = EvaluatorContractRecord(id="eval-003", name="replay-check", required_prerequisites=["context_resolved"])
        evaluator = ReplayabilityFailureEvaluator(contract)
        record = _make_record(resolution_trace_id="")
        context = _make_context()
        result = evaluator.evaluate(record, context, {})
        assert result.status == "skipped"


# ── BaseEvaluator unit tests ──


class TestBaseEvaluator:
    def test_skip_assessment(self) -> None:
        contract = EvaluatorContractRecord(id="eval-base", name="base")
        evaluator = BaseEvaluator(contract)
        record = _make_record()
        result = evaluator.skip_assessment(record, ["context_resolved", "context_bindings"])
        assert result.status == "skipped"
        assert "context_resolved" in result.summary
        assert result.details["missing_prerequisites"] == ["context_resolved", "context_bindings"]

    def test_check_prerequisites_all_present(self) -> None:
        contract = EvaluatorContractRecord(
            id="eval-base",
            name="base",
            required_prerequisites=["context_resolved", "context_bindings", "source_resources"],
        )
        evaluator = BaseEvaluator(contract)
        record = _make_record()
        context = _make_context()
        missing = evaluator.check_prerequisites(record, context)
        assert missing == []

    def test_check_prerequisites_missing(self) -> None:
        contract = EvaluatorContractRecord(
            id="eval-base",
            name="base",
            required_prerequisites=["context_resolved", "context_bindings", "link_assertions"],
        )
        evaluator = BaseEvaluator(contract)
        record = _make_record(binding_ids=(), resolution_trace_id="", source_ids=())
        context = _make_context()
        missing = evaluator.check_prerequisites(record, context)
        assert "context_resolved" in missing
        assert "context_bindings" in missing
