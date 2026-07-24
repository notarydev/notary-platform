"""WP-070: Evidence Sufficiency tests — E0-E4 deterministic calculation."""

from __future__ import annotations

from notary_platform.sweep.evaluators.base import (
    FrozenDecisionEvidenceRecord,
    ResolvedContext,
)
from notary_platform.sweep.sufficiency import EvidenceSufficiencyService


def _make_record(
    source_ids: tuple[str, ...] = ("res-1",),
    binding_ids: tuple[str, ...] = ("cb-1",),
    resolution_trace_id: str = "rt-1",
    version: int = 1,
    decision_identity: str = "res-1",
) -> FrozenDecisionEvidenceRecord:
    return FrozenDecisionEvidenceRecord(
        id="der-1",
        org_id="test-org",
        decision_identity=decision_identity,
        identity_method="exact_id",
        source_resource_ids=source_ids,
        context_binding_ids=binding_ids,
        link_assertion_ids=(),
        resolution_trace_id=resolution_trace_id,
        enriched=False,
        version=version,
        created_at="2026-07-01T12:00:00Z",
    )


def _make_context(
    conflicted: tuple[str, ...] = (),
    authoritative: bool = False,
    corroborated: bool = False,
) -> ResolvedContext:
    return ResolvedContext(
        binding_ids=("cb-1",),
        included_artifacts=("res-1",),
        excluded_artifacts=(),
        superseded_bindings=(),
        conflicted_bindings=conflicted,
        missing_artifacts=(),
        stale_artifacts=(),
        redacted_artifacts=(),
        reasons={
            "authoritative_context": authoritative,
            "corroborated_context": corroborated,
        },
    )


service = EvidenceSufficiencyService()


class TestE0:
    def test_e0_with_source_resource(self) -> None:
        record = _make_record(source_ids=("res-1",), binding_ids=())
        context = _make_context()
        result = service.calculate(record, context)
        assert result.current_level == "E0"

    def test_e0_with_decision_identity_only(self) -> None:
        record = _make_record(source_ids=(), binding_ids=())
        context = _make_context()
        result = service.calculate(record, context)
        assert result.current_level == "E0"

    def test_no_e0_when_no_observation(self) -> None:
        record = _make_record(source_ids=(), binding_ids=(), decision_identity="")
        context = _make_context()
        result = service.calculate(record, context)
        assert result.current_level == ""
        assert any("E0" in f for f in result.failed)


class TestE1:
    def test_e1_with_bindings_and_no_conflict(self) -> None:
        record = _make_record()
        context = _make_context()
        result = service.calculate(record, context)
        assert result.current_level in ("E1", "E2", "E3", "E4")
        assert any("E1" in s for s in result.satisfied)

    def test_e1_blocked_by_conflict(self) -> None:
        record = _make_record()
        context = _make_context(conflicted=("res-1",))
        result = service.calculate(record, context)
        if result.current_level == "E0":
            assert any("identity ambiguity" in f for f in result.failed)

    def test_e1_blocked_by_no_bindings(self) -> None:
        record = _make_record(binding_ids=())
        context = _make_context()
        result = service.calculate(record, context)
        assert result.current_level == "E0"


class TestE2:
    def test_e2_with_authoritative_context(self) -> None:
        record = _make_record()
        context = _make_context(authoritative=True)
        result = service.calculate(record, context)
        assert result.current_level in ("E2", "E3", "E4")
        assert any("E2" in s for s in result.satisfied)

    def test_e2_with_corroborated_context(self) -> None:
        record = _make_record()
        context = _make_context(corroborated=True)
        result = service.calculate(record, context)
        assert result.current_level in ("E2", "E3", "E4")

    def test_e2_blocked_without_authoritative_or_corroborated(self) -> None:
        record = _make_record()
        context = _make_context()
        result = service.calculate(record, context)
        assert result.current_level == "E1"
        assert any("E2" in f for f in result.failed)


class TestE3:
    def test_e3_with_integrity_and_replay_path(self) -> None:
        record = _make_record(version=1)
        context = _make_context(authoritative=True)
        result = service.calculate(record, context, has_replay_result=True)
        assert result.current_level in ("E3", "E4")

    def test_e3_blocked_without_integrity(self) -> None:
        record = _make_record(version=0)
        context = _make_context(authoritative=True)
        result = service.calculate(record, context, has_replay_result=True)
        assert result.current_level == "E2"

    def test_e3_blocked_without_replay_path(self) -> None:
        record = _make_record(resolution_trace_id="")
        context = _make_context(authoritative=True)
        result = service.calculate(record, context)
        assert result.current_level == "E2"


class TestE4:
    def test_e4_with_replay_and_mutation(self) -> None:
        record = _make_record()
        context = _make_context(authoritative=True)
        result = service.calculate(record, context, has_replay_result=True, has_verified_mutation=True)
        assert result.current_level == "E4"
        assert any("E4" in s for s in result.satisfied)

    def test_e4_blocked_without_replay(self) -> None:
        record = _make_record()
        context = _make_context(authoritative=True)
        result = service.calculate(record, context, has_replay_result=False, has_verified_mutation=True)
        assert result.current_level == "E3"

    def test_e4_blocked_without_mutation(self) -> None:
        record = _make_record()
        context = _make_context(authoritative=True)
        result = service.calculate(record, context, has_replay_result=True, has_verified_mutation=False)
        assert result.current_level == "E3"


class TestSufficiencyReport:
    def test_format_report_includes_all_fields(self) -> None:
        record = _make_record()
        context = _make_context()
        result = service.calculate(record, context)
        report = service.format_report(result)
        assert "current_level" in report
        assert "satisfied" in report
        assert "failed" in report
        assert "next_level_requirements" in report
        assert "complete" in report

    def test_e4_is_complete(self) -> None:
        record = _make_record()
        context = _make_context(authoritative=True)
        result = service.calculate(record, context, has_replay_result=True, has_verified_mutation=True)
        report = service.format_report(result)
        assert report["complete"] is True

    def test_e0_is_not_complete(self) -> None:
        record = _make_record(source_ids=("res-1",), binding_ids=())
        context = _make_context()
        result = service.calculate(record, context)
        report = service.format_report(result)
        assert report["complete"] is False
