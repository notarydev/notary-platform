"""Product workflow services for the Notary Platform vertical slice (WO-28).

These services own the workflow rules that drive the active product horizon.
They are intentionally written against the in-memory storage backend first; the
storage abstraction can be hardened to Postgres/S3 later without changing the
product logic.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Optional

from notary_platform.certificates import generate_certificate, verify_certificate_signature
from notary_platform.demo_scenarios import SCENARIOS, get_scenario
from notary_platform.models import (
    ActionEligibility,
    AIExecutionEvent,
    DataSourceType,
    EventKind,
    EvidenceArtifact,
    FixReference,
    HumanLabel,
    Incident,
    IncidentStatus,
    KnownLimitation,
    MutationTest,
    ProofCertificate,
    ProofClaim,
    ReadinessCheck,
    ReadinessPolicy,
    ReleaseGateResult,
    ReplayabilityStatus,
    ReplayRun,
    Scenario,
    ScenarioCandidate,
    ScenarioRun,
    ScenarioRunResult,
    VerificationRecord,
)
from notary_platform.replay_engine.cassette import ResponseCassette
from notary_platform.replay_engine.replay import replay_snapshot
from notary_platform.storage import StorageBackend
from notary_platform.storage import get_storage as _get_storage

# ---------------------------------------------------------------------------
# Agent factory registry
# ---------------------------------------------------------------------------


def _scenario_agent_factory(scenario_id: str) -> Callable[..., str]:
    """Return a deterministic demo agent for a scenario."""
    scenario = get_scenario(scenario_id)

    def agent(cassette: ResponseCassette, **kwargs: Any) -> str:
        mode = kwargs.get("mode", "default")
        if scenario.scenario_id == "harborline-personal-loan-adverse-action":
            recorded = dict(scenario.cassette_response)
            result = cassette.lookup("POST", "https://demo.notary.local/credit-bureau")
            if result is not None and isinstance(result.get("response"), dict):
                recorded.update(result["response"])

            evidence_status = str(recorded.get("bureau_evidence_status", "")).lower()
            policy_band = str(recorded.get("policy_band", "")).lower()
            score = int(recorded.get("credit_score", recorded.get("score", 0)) or 0)
            review_worthy = (
                recorded.get("income_verified") is True
                and (
                    evidence_status.startswith("missing")
                    or policy_band == "borderline_review"
                    or 660 <= score <= 700
                )
            )
            fix_enabled = bool(
                kwargs.get("route_missing_or_borderline_bureau_to_underwriting_review")
                or mode == "fixed"
            )
            if fix_enabled and review_worthy:
                return "UNDERWRITING_REVIEW"
            return "DENY"

        if scenario.scenario_id == "lending-denial":
            threshold = int(kwargs.get("threshold", 700))
            result = cassette.lookup("POST", "https://demo.notary.local/credit-api")
            score = scenario.cassette_response.get("score", 0)
            if result is not None and isinstance(result.get("response"), dict):
                score = result["response"].get("score", score)
            return "APPROVE" if int(score) >= threshold else "DENY"

        if scenario.scenario_id == "prior-auth-denial":
            if kwargs.get("require_human_review_for_high_risk_note") or mode == "fixed":
                return "ESCALATE_TO_HUMAN_REVIEW"
            return "DENY"

        if scenario.scenario_id == "hiring-screen-rejection":
            if kwargs.get("remove_age_proxy") or mode == "fixed":
                return "ADVANCE_TO_REVIEW"
            return "REJECT"

        if scenario.scenario_id == "customer-service-handoff":
            recorded = dict(scenario.cassette_response)
            try:
                intent_lookup = cassette.lookup("POST", "https://demo.notary.local/intent-classifier")
                if intent_lookup is not None and isinstance(intent_lookup.get("response"), dict):
                    recorded.update(intent_lookup["response"])
            except Exception:
                pass
            human_request_count = int(recorded.get("human_request_count", 0))
            negative_sentiment = str(recorded.get("sentiment", "")).lower() == "negative"
            enforce = bool(kwargs.get("escalate_after_repeated_human_request") or mode == "fixed")
            if enforce and (human_request_count >= 2 or negative_sentiment):
                return "ESCALATE_TO_HUMAN"
            return "CONTINUE_BOT"

        return scenario.original_decision

    return agent


# ---------------------------------------------------------------------------
# Service registry
# ---------------------------------------------------------------------------


class ServiceRegistry:
    """Holds the shared storage backend and agent factory for services."""

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self.storage = storage or _get_storage()
        self._agent_factory: Callable[[str], Callable[..., str]] = _scenario_agent_factory

    def get_agent(self, scenario_id: str) -> Callable[..., str]:
        return self._agent_factory(scenario_id)


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------


class IngestionService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def _next_vr_id(self) -> str:
        return f"vr-{uuid.uuid4().hex[:8]}"

    def _snapshot_from_vr(self, vr: VerificationRecord) -> dict[str, Any]:
        """Reconstruct a replay-engine snapshot from a VR's events."""
        elements: list[dict[str, Any]] = []
        for e in vr.events:
            payload = dict(e.payload)
            if e.kind == EventKind.tool_call:
                # Ensure replay-engine cassette can match this entry.
                if "request" not in payload:
                    payload = {
                        "request": {
                            "method": payload.get("method", "POST"),
                            "url": payload.get("url", "https://demo.notary.local/" + e.source_system),
                            "body": payload.get("body", ""),
                        },
                        "response": payload.get("response", {}),
                        "status": payload.get("status", 200),
                    }
            elements.append({"kind": e.kind.value, "payload": payload})
        return {
            "schema_version": 1,
            "timestamp": vr.created_at,
            "elements": elements,
            "merkle_chain": [],
            "root_hash": vr.root_hash,
        }

    def _create_evidence(self, vr: VerificationRecord, kind: str, payload: dict[str, Any]) -> EvidenceArtifact:
        artifact = EvidenceArtifact(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            verification_record_id=vr.id,
            kind=kind,
            reference="",
            payload=payload,
        )
        return self.storage.create_evidence_artifact(artifact)

    def create_from_sdk_snapshot(
        self,
        snapshot: dict[str, Any],
        org_id: str,
        agent_id: str = "",
        environment_id: str = "env:demo",
        promoted_to_incident: str = "",
    ) -> VerificationRecord:
        from notary_platform.models import sdk_element_to_event

        vr_id = self._next_vr_id()
        events = [sdk_element_to_event(e, i) for i, e in enumerate(snapshot.get("elements", []))]
        vr = VerificationRecord(
            id=vr_id,
            org_id=org_id,
            environment_id=environment_id,
            source_type=DataSourceType.sdk_snapshot,
            agent_id=agent_id,
            events=events,
            root_hash=snapshot.get("root_hash", ""),
            agent_version=snapshot.get("agent_version", ""),
            model_provider=snapshot.get("model_provider", ""),
            model_name=snapshot.get("model_name", ""),
            policy_version=snapshot.get("policy_version", ""),
            promoted_to_incident=promoted_to_incident,
        )
        self._create_evidence(vr, "snapshot", snapshot)
        replayability = ReplayabilityService(self.registry)
        vr.replayability, vr.replayability_reason, vr.missing_prerequisites = replayability.assess(vr)
        return self.storage.create_vr(vr)

    def create_from_api_submission(
        self,
        org_id: str,
        source_system_id: str = "",
        source_record_ref: str = "",
        external_ref: str = "",
        agent_id: str = "",
        agent_version: str = "",
        expected_outcome: str = "",
        environment_id: str = "env:demo",
    ) -> VerificationRecord:
        vr = VerificationRecord(
            id=self._next_vr_id(),
            org_id=org_id,
            environment_id=environment_id,
            source_type=DataSourceType.api_submission,
            source_system_id=source_system_id,
            source_record_ref=source_record_ref or external_ref,
            external_ref=external_ref,
            agent_id=agent_id,
            agent_version=agent_version,
            expected_outcome=expected_outcome,
        )
        replayability = ReplayabilityService(self.registry)
        vr.replayability, vr.replayability_reason, vr.missing_prerequisites = replayability.assess(vr)
        return self.storage.create_vr(vr)

    def create_manual(
        self,
        org_id: str,
        payload: dict[str, Any],
        environment_id: str = "env:demo",
    ) -> VerificationRecord:
        events: list[AIExecutionEvent] = []
        if payload.get("transcript"):
            events.append(
                AIExecutionEvent(
                    id=uuid.uuid4().hex,
                    kind=EventKind.human_action,
                    payload={"transcript": str(payload["transcript"])[:500]},
                    order=0,
                )
            )
        if payload.get("decision"):
            events.append(
                AIExecutionEvent(
                    id=uuid.uuid4().hex,
                    kind=EventKind.decision,
                    payload={"decision": payload["decision"]},
                    order=1,
                )
            )
        vr = VerificationRecord(
            id=self._next_vr_id(),
            org_id=org_id,
            environment_id=environment_id,
            source_type=DataSourceType.manual_submission,
            external_ref=payload.get("ticket_id", ""),
            agent_id=payload.get("agent_id", ""),
            business_function=payload.get("business_function", ""),
            events=events,
            source_system_id=payload.get("source_system_id", ""),
            source_record_ref=payload.get("source_record_ref", ""),
            is_demo=payload.get("is_demo", False),
        )
        replayability = ReplayabilityService(self.registry)
        vr.replayability, vr.replayability_reason, vr.missing_prerequisites = replayability.assess(vr)
        return self.storage.create_vr(vr)

    def create_webhook(
        self,
        org_id: str,
        payload: dict[str, Any],
        environment_id: str = "env:demo",
    ) -> VerificationRecord:
        events_data = payload.get("events", [])
        events: list[AIExecutionEvent] = []
        for i, e in enumerate(events_data):
            kind_str = e.get("kind", "model_call")
            try:
                kind = EventKind(kind_str)
            except ValueError:
                kind = EventKind.decision
            events.append(
                AIExecutionEvent(
                    id=uuid.uuid4().hex,
                    kind=kind,
                    payload=e.get("payload", {}),
                    order=i,
                )
            )
        if not events:
            events = [AIExecutionEvent(id=uuid.uuid4().hex, kind=EventKind.decision, payload=payload, order=0)]
        vr = VerificationRecord(
            id=self._next_vr_id(),
            org_id=org_id,
            environment_id=environment_id,
            source_type=DataSourceType.webhook,
            external_ref=payload.get("source_id", ""),
            events=events,
            source_system_id=payload.get("source_system_id", ""),
            source_record_ref=payload.get("source_record_ref", ""),
        )
        replayability = ReplayabilityService(self.registry)
        vr.replayability, vr.replayability_reason, vr.missing_prerequisites = replayability.assess(vr)
        return self.storage.create_vr(vr)

    def create_incident_from_vr(self, vr: VerificationRecord) -> Incident:
        snapshot = self._snapshot_from_vr(vr)
        incident = self.storage.create_incident(snapshot, org_id=vr.org_id)
        incident._record_custody("ingested", actor="ingestion_service", detail=f"from vr {vr.id}")
        self.storage.update_incident(incident)
        self.storage.persist_evidence(incident.incident_id, "snapshot", snapshot)
        vr.promoted_to_incident = incident.incident_id
        self.storage.update_vr(vr)
        return incident


# ---------------------------------------------------------------------------
# Replayability service
# ---------------------------------------------------------------------------


class ReplayabilityService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def assess(self, vr: VerificationRecord) -> tuple[ReplayabilityStatus, str, list[str]]:
        has_llm = any(e.kind == EventKind.model_call for e in vr.events)
        has_cassette = any(e.kind in (EventKind.api_response, EventKind.tool_call) for e in vr.events)
        has_decision = any(e.kind == EventKind.decision for e in vr.events)
        has_label = bool(vr.current_label_id)
        missing: list[str] = []

        score, flags = self._compute_determinism(vr)
        vr.replayability_score = score
        vr.non_deterministic_flags = [f.to_dict() for f in flags]

        if has_llm and not has_cassette:
            state = ReplayabilityStatus.evidence_only
            msg = "LLM outputs are non-deterministic. Replay can verify conditions but not exact outputs."
        elif not has_cassette and not has_llm and not has_decision:
            state = ReplayabilityStatus.missing_context
            msg = "No recorded responses, model calls, or decisions found in this record."
            missing.append("cassette_data")
        elif has_cassette and not has_label:
            state = ReplayabilityStatus.requires_human_label
            msg = "Cassette data is present but no expected outcome label has been added."
            missing.append("human_label")
        elif has_cassette and has_label and has_decision:
            state = ReplayabilityStatus.replayable
            msg = "All prerequisites met: cassette data, human label, and decision present."
        elif has_llm and has_cassette:
            state = ReplayabilityStatus.partially_replayable
            msg = "LLM call present; replay can verify recorded system responses but LLM outputs may differ."
        else:
            state = ReplayabilityStatus.unknown
            msg = "Replayability could not be determined."

        if score >= 0.8 and state == ReplayabilityStatus.replayable:
            vr.defensibility_summary = f"{int(score*100)}% of the decision path is deterministically re-testable."
        elif score >= 0.5:
            vr.defensibility_summary = f"{int(score*100)}% deterministically re-testable. Remaining relies on sealed evidence assumptions."
        else:
            vr.defensibility_summary = f"Evidence-only: {int(score*100)}% deterministically testable. Manual verification required."

        return state, msg, missing

    def _compute_determinism(self, vr: VerificationRecord) -> tuple[float, list[KnownLimitation]]:
        total_weight = 10.0
        penalty = 0.0
        flags: list[KnownLimitation] = []
        llm_events = [e for e in vr.events if e.kind == EventKind.model_call]
        has_llm = bool(llm_events)
        has_http = any(e.kind in (EventKind.tool_call, EventKind.api_response) for e in vr.events)

        if has_llm:
            # Deterministic LLM params reduce the severity of the limitation.
            def _deterministic_llm_payload(payload: dict[str, Any]) -> bool:
                raw_metadata = payload.get("metadata")
                metadata: dict[Any, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
                temperature = payload.get("temperature", metadata.get("temperature"))
                seed = payload.get("seed", metadata.get("seed"))
                return temperature == 0.0 and seed is not None

            deterministic_llm = all(
                _deterministic_llm_payload(e.payload)
                for e in llm_events
            )
            if deterministic_llm:
                penalty += 1.0
                flags.append(
                    KnownLimitation(
                        code="llm_call",
                        severity="NON_DETERMINISTIC_SIDE_EFFECT",
                        message="LLM uses temp=0 and seed; outputs should be reproducible but model drift is still possible.",
                        subject="model_interaction",
                        certificate_blocking=False,
                        remediation="Pin model version and monitor for drift.",
                    )
                )
            else:
                penalty += 3.0
                flags.append(
                    KnownLimitation(
                        code="llm_call",
                        severity="NON_DETERMINISTIC_CORE",
                        message="LLM outputs are non-deterministic. May differ on replay.",
                        subject="model_interaction",
                        certificate_blocking=True,
                        remediation="Use temp=0 or seed.",
                    )
                )
        if not has_http:
            penalty += 2.0
            flags.append(
                KnownLimitation(
                    code="missing_cassette",
                    severity="NON_DETERMINISTIC_CORE",
                    message="No recorded API/tool responses. Cannot replay.",
                    subject="external_calls",
                    certificate_blocking=True,
                    remediation="Capture all API calls with responses.",
                )
            )
        if not vr.current_label_id:
            penalty += 1.5
            flags.append(
                KnownLimitation(
                    code="missing_label",
                    severity="NON_DETERMINISTIC_SIDE_EFFECT",
                    message="No expected outcome label.",
                    subject="human_review",
                    certificate_blocking=True,
                    remediation="Add approved expected outcome.",
                )
            )
        if not any(e.kind == EventKind.decision for e in vr.events):
            penalty += 1.0
            flags.append(
                KnownLimitation(
                    code="missing_decision",
                    severity="NON_DETERMINISTIC_CORE",
                    message="No decision event captured.",
                    subject="decision_path",
                    certificate_blocking=True,
                    remediation="Capture final decision in SDK.",
                )
            )

        score = max(0.0, min(1.0, 1.0 - (penalty / total_weight)))
        return score, flags


# ---------------------------------------------------------------------------
# Replay service
# ---------------------------------------------------------------------------


class ReplayService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def _snapshot_from_vr(self, vr: VerificationRecord) -> dict[str, Any]:
        elements: list[dict[str, Any]] = []
        for e in vr.events:
            payload = dict(e.payload)
            if e.kind == EventKind.tool_call:
                if "request" not in payload:
                    payload = {
                        "request": {
                            "method": payload.get("method", "POST"),
                            "url": payload.get("url", "https://demo.notary.local/" + e.source_system),
                            "body": payload.get("body", ""),
                        },
                        "response": payload.get("response", {}),
                        "status": payload.get("status", 200),
                    }
            elements.append({"kind": e.kind.value, "payload": payload})
        return {
            "schema_version": 1,
            "timestamp": vr.created_at,
            "elements": elements,
            "merkle_chain": [],
            "root_hash": vr.root_hash,
        }

    def _find_decision(self, vr: VerificationRecord) -> str:
        for e in vr.events:
            if e.kind == EventKind.decision:
                return str(e.payload.get("decision", ""))
        return ""

    def _find_scenario(self, vr: VerificationRecord) -> str:
        for sid in SCENARIOS:
            if sid in vr.source_system_id or sid in vr.agent_id:
                return sid
        # Try to match by business title or source record ref
        for sid, scenario in SCENARIOS.items():
            if scenario.title.lower() in (vr.business_function or "").lower():
                return sid
        return "lending-denial"

    def run_replay(self, vr_id: str, org_id: str) -> ReplayRun:
        vr = self.storage.get_vr(vr_id)
        if vr is None or vr.org_id != org_id:
            raise ValueError("Verification Record not found")

        # Check replayability: missing_context and evidence_only cannot produce a meaningful replay.
        if vr.replayability in (ReplayabilityStatus.missing_context, ReplayabilityStatus.evidence_only):
            run = ReplayRun(
                id=f"rr-{uuid.uuid4().hex[:8]}",
                org_id=vr.org_id,
                verification_record_id=vr.id,
                incident_id=vr.promoted_to_incident,
                original_decision=self._find_decision(vr),
                replay_method="none",
                status="incomplete",
            )
            run.known_limitations.append(
                KnownLimitation(
                    code="missing_cassette_context",
                    severity="NON_DETERMINISTIC_CORE",
                    message=f"Record is {vr.replayability.value}: no cassette data available for replay.",
                    subject="replay",
                    certificate_blocking=True,
                )
            )
            self.storage.create_replay_run(run)
            return run

        scenario_id = self._find_scenario(vr)
        agent_fn = self.registry.get_agent(scenario_id)
        snapshot = self._snapshot_from_vr(vr)

        run = ReplayRun(
            id=f"rr-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            verification_record_id=vr.id,
            incident_id=vr.promoted_to_incident,
            original_decision=self._find_decision(vr),
            replay_method="cassette",
        )

        try:
            result = replay_snapshot(snapshot, agent_fn)
            run.replayed_decision = result.get("decision") or ""
            status = result.get("replay_status", "error")
            if status == "replayed":
                run.status = "replayed"
            else:
                run.status = status
                if run.status == "escalation_required":
                    run.missing_calls.append("cassette_lookup_failed")
        except Exception as exc:
            run.status = "error"
            run.known_limitations.append(
                KnownLimitation(
                    code="replay_error",
                    severity="NON_DETERMINISTIC_CORE",
                    message=str(exc),
                    subject="replay_engine",
                    certificate_blocking=True,
                )
            )

        # If replay produced a different decision, that is a non-determinism signal.
        if run.replayed_decision and run.original_decision and run.replayed_decision != run.original_decision:
            run.known_limitations.append(
                KnownLimitation(
                    code="decision_mismatch",
                    severity="NON_DETERMINISTIC_SIDE_EFFECT",
                    message=f"Replayed decision ({run.replayed_decision}) differs from recorded decision ({run.original_decision}).",
                    subject="replay",
                    certificate_blocking=False,
                    remediation="Review deterministic controls (temp=0, seed, sealed cassette).",
                )
            )

        artifact = EvidenceArtifact(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            verification_record_id=vr.id,
            kind="replay_result",
            reference="",
            payload=run.to_dict(),
        )
        self.storage.create_evidence_artifact(artifact)
        run.evidence_refs.append(artifact.id)

        self.storage.create_replay_run(run)

        # Update incident status if this VR was promoted.
        if vr.promoted_to_incident:
            incident = self.storage.get_incident(vr.promoted_to_incident)
            if incident is not None:
                incident.replay_result = {
                    "decision": run.replayed_decision,
                    "replay_status": run.status,
                    "replay_run_id": run.id,
                    "original_decision": run.original_decision,
                }
                if run.status == "replayed":
                    incident.status = IncidentStatus.replayed
                incident._record_custody("replayed", actor="replay_service", detail=f"run={run.id}")
                self.storage.update_incident(incident)

        return run


# ---------------------------------------------------------------------------
# Mutation service
# ---------------------------------------------------------------------------


class MutationService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def _snapshot_from_vr(self, vr: VerificationRecord) -> dict[str, Any]:
        ingestion = IngestionService(self.registry)
        return ingestion._snapshot_from_vr(vr)

    def _find_scenario(self, vr: VerificationRecord) -> str:
        replay = ReplayService(self.registry)
        return replay._find_scenario(vr)

    def run_mutation(
        self,
        vr_id: str,
        org_id: str,
        fix_config: dict[str, Any],
        expected_correct_behavior: str = "",
    ) -> MutationTest:
        vr = self.storage.get_vr(vr_id)
        if vr is None or vr.org_id != org_id:
            raise ValueError("Verification Record not found")

        # Require a prior replay run.
        replay_runs = self.storage.list_replay_runs_for_vr(vr_id)
        if not replay_runs:
            raise ValueError("Mutation requires a reproduced replay run")
        replay_run = replay_runs[-1]
        if replay_run.status != "replayed":
            raise ValueError(f"Replay not successful: {replay_run.status}")

        # Require an approved label for certificate-grade proof.
        label = None
        if vr.current_label_id:
            label = self.storage.get_label(vr.current_label_id)
        expected = expected_correct_behavior or (label.expected_outcome if label else "")
        if not expected:
            raise ValueError("Expected outcome is required for mutation test")

        scenario_id = self._find_scenario(vr)
        agent_fn = self.registry.get_agent(scenario_id)
        snapshot = self._snapshot_from_vr(vr)

        test = MutationTest(
            id=f"mt-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            verification_record_id=vr.id,
            incident_id=vr.promoted_to_incident,
            replay_run_id=replay_run.id,
            fix_reference=FixReference(id=f"fix-{uuid.uuid4().hex[:6]}", config=fix_config, description="Fix applied for mutation test", agent_id=vr.agent_id),
            expected_outcome=expected,
            label_id=vr.current_label_id,
            original_decision=replay_run.original_decision,
            replay_method="cassette",
        )

        try:
            from notary_platform.replay_engine.mutation import run_mutation as _run_mutation

            result = _run_mutation(snapshot, agent_fn, fix_config, expected_correct_behavior=expected)
            test.mutated_decision = result.get("mutated_decision") or ""
            test.verdict = "verified" if result.get("mitigated") else "not_verified"
        except Exception as exc:
            test.verdict = "error"
            test.known_limitations.append(
                KnownLimitation(
                    code="mutation_error",
                    severity="NON_DETERMINISTIC_CORE",
                    message=str(exc),
                    subject="mutation_engine",
                    certificate_blocking=True,
                )
            )

        artifact = EvidenceArtifact(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            verification_record_id=vr.id,
            kind="mutation_result",
            reference="",
            payload=test.to_dict(),
        )
        self.storage.create_evidence_artifact(artifact)
        test.evidence_refs.append(artifact.id)

        self.storage.create_mutation_test(test)

        if vr.promoted_to_incident:
            incident = self.storage.get_incident(vr.promoted_to_incident)
            if incident is not None:
                incident.mutation_result = {
                    "original_decision": test.original_decision,
                    "mutated_decision": test.mutated_decision,
                    "mitigated": test.verdict == "verified",
                    "fix_config": fix_config,
                    "expected_correct_behavior": expected,
                    "mutation_test_id": test.id,
                }
                if test.verdict == "verified":
                    incident.status = IncidentStatus.mitigated
                incident._record_custody("mutation_tested", actor="mutation_service", detail=f"test={test.id}")
                self.storage.update_incident(incident)

        return test


# ---------------------------------------------------------------------------
# Label provenance service
# ---------------------------------------------------------------------------


class LabelProvenanceService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def create_label(
        self,
        vr_id: str,
        org_id: str,
        expected_outcome: str,
        reviewer: str = "",
        role: str = "",
        reason: str = "",
        suggested_by: str = "",
        suggested_confidence: float = 1.0,
    ) -> HumanLabel:
        vr = self.storage.get_vr(vr_id)
        if vr is None or vr.org_id != org_id:
            raise ValueError("Verification Record not found")

        label = HumanLabel(
            id=uuid.uuid4().hex,
            verification_record_id=vr_id,
            expected_outcome=expected_outcome,
            reviewer=reviewer,
            role=role,
            reason=reason,
            suggested_by=suggested_by,
            suggested_confidence=suggested_confidence,
            approval_reason="Approved" if not suggested_by else "",
            status="active" if not suggested_by else "suggested",
        )
        self.storage.create_label(label)
        vr.current_label_id = label.id
        vr.label_source = "human" if not suggested_by else suggested_by
        replayability = ReplayabilityService(self.registry)
        vr.replayability, vr.replayability_reason, vr.missing_prerequisites = replayability.assess(vr)
        self.storage.update_vr(vr)
        return label

    def approve_suggested_label(self, vr_id: str, org_id: str) -> HumanLabel:
        vr = self.storage.get_vr(vr_id)
        if vr is None or vr.org_id != org_id:
            raise ValueError("Verification Record not found")
        if not vr.current_label_id:
            raise ValueError("No suggested label to approve")
        label = self.storage.get_label(vr.current_label_id)
        if label is None:
            raise ValueError("Label not found")
        label.status = "active"
        label.approval_reason = "Approved from suggested label"
        self.storage.create_label(label)
        replayability = ReplayabilityService(self.registry)
        vr.replayability, vr.replayability_reason, vr.missing_prerequisites = replayability.assess(vr)
        self.storage.update_vr(vr)
        return label


# ---------------------------------------------------------------------------
# Known limitation service
# ---------------------------------------------------------------------------


class KnownLimitationService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def from_vr_and_replay(self, vr: VerificationRecord, replay: ReplayRun | None) -> list[KnownLimitation]:
        limitations: list[KnownLimitation] = []
        for f in vr.non_deterministic_flags:
            code = f.get("component") or f.get("code", "unknown")
            severity = f.get("severity", "NON_DETERMINISTIC_SIDE_EFFECT")
            limitations.append(
                KnownLimitation(
                    code=code,
                    severity=severity,
                    message=f.get("description", ""),
                    subject=f.get("location", ""),
                    certificate_blocking=severity == "NON_DETERMINISTIC_CORE",
                    remediation=f.get("remediation", ""),
                )
            )
        if replay:
            for lim in replay.known_limitations:
                limitations.append(lim)
        return limitations

    def from_mutation(self, mutation: MutationTest) -> list[KnownLimitation]:
        return list(mutation.known_limitations)

    def blocking(self, limitations: list[KnownLimitation]) -> list[KnownLimitation]:
        return [lim for lim in limitations if lim.certificate_blocking]

    def certificate_eligible(self, limitations: list[KnownLimitation]) -> bool:
        return not any(lim.certificate_blocking for lim in limitations)


# ---------------------------------------------------------------------------
# Proof claim service
# ---------------------------------------------------------------------------


class ProofClaimService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def create_claim(
        self,
        vr: VerificationRecord,
        mutation: MutationTest,
        scenario: Scenario | None,
        scenario_run_id: str = "",
    ) -> ProofClaim:
        limitations = KnownLimitationService(self.registry).from_vr_and_replay(vr, None)
        for lim in mutation.known_limitations:
            limitations.append(lim)

        return ProofClaim(
            id=f"pc-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            scenario_id=scenario.id if scenario else "",
            scenario_run_id=scenario_run_id,
            agent_version=vr.agent_version,
            fix_reference=mutation.fix_reference,
            release_context="",
            expected_outcome=mutation.expected_outcome,
            label_id=mutation.label_id,
            replay_method=mutation.replay_method,
            known_limitations=limitations,
        )


# ---------------------------------------------------------------------------
# Certificate service
# ---------------------------------------------------------------------------


class CertificateService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def issue_proof_of_mitigation(self, vr_id: str, org_id: str) -> ProofCertificate:
        vr = self.storage.get_vr(vr_id)
        if vr is None or vr.org_id != org_id:
            raise ValueError("Verification Record not found")

        mutations = self.storage.list_mutation_tests_for_vr(vr_id)
        if not mutations:
            raise ValueError("Proof requires a verified mutation test")
        mutation = mutations[-1]
        if mutation.verdict != "verified":
            raise ValueError(f"Mutation test not verified: {mutation.verdict}")

        limitations = KnownLimitationService(self.registry).from_vr_and_replay(vr, None)
        for lim in mutation.known_limitations:
            limitations.append(lim)

        if not KnownLimitationService(self.registry).certificate_eligible(limitations):
            blocking = KnownLimitationService(self.registry).blocking(limitations)
            raise ValueError(f"Certificate blocked by limitations: {[lim.code for lim in blocking]}")

        # Find or create a Scenario for the claim.
        scenarios = [s for s in self.storage.list_scenarios(org_id) if s.source_vr_id == vr_id]
        scenario = scenarios[0] if scenarios else None

        claim = ProofClaimService(self.registry).create_claim(vr, mutation, scenario)

        # Legacy signed dict for verification compatibility.
        signed_dict = generate_certificate(
            incident_id=vr.promoted_to_incident or vr.id,
            root_hash=vr.root_hash,
            integrity_status="verified" if vr.root_hash else "unverified",
            replay_result={
                "decision": mutation.mutated_decision,
                "replay_status": "replayed",
                "replay_method": mutation.replay_method,
            },
            original_decision=mutation.original_decision,
            mutated_decision=mutation.mutated_decision,
            fix_config=mutation.fix_reference.config,
            expected_correct_behavior=mutation.expected_outcome,
            timestamp=vr.created_at,
        )

        cert = ProofCertificate(
            id=f"pom-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            certificate_id=signed_dict.get("certificate_id", "pom-cert-v1"),
            certificate_type="proof_of_mitigation",
            subject_id=vr.promoted_to_incident or vr.id,
            claim=claim,
            issued_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            signature=signed_dict.get("signature", ""),
            signed_payload=signed_dict,
            integrity_status="verified" if vr.root_hash else "unverified",
            known_limitations=limitations,
        )

        self.storage.create_proof_certificate(cert)

        artifact = EvidenceArtifact(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            org_id=vr.org_id,
            verification_record_id=vr.id,
            kind="certificate",
            reference="",
            payload=cert.to_dict(),
        )
        self.storage.create_evidence_artifact(artifact)

        if vr.promoted_to_incident:
            incident = self.storage.get_incident(vr.promoted_to_incident)
            if incident is not None:
                incident.certificate = signed_dict
                incident.status = IncidentStatus.certified
                incident._record_custody("certified", actor="certificate_service", detail=f"cert={cert.id}")
                self.storage.update_incident(incident)
                self.storage.store_certificate(incident.incident_id, signed_dict)

        return cert

    def verify(self, certificate_id: str) -> bool:
        cert = self.storage.get_proof_certificate(certificate_id)
        if cert is None:
            return False
        return verify_certificate_signature(cert.signed_payload)

    def issue_proof_of_readiness(self, readiness_check: ReadinessCheck) -> ProofCertificate:
        policy = self.storage.get_readiness_policy(readiness_check.policy_id)
        if policy is None:
            raise ValueError("Readiness policy not found")

        claim = ProofClaim(
            id=f"pc-{uuid.uuid4().hex[:8]}",
            org_id=readiness_check.org_id,
            scenario_run_id=readiness_check.scenario_run_id,
            agent_version=readiness_check.agent_version,
            release_context="release_gate",
            expected_outcome="all_required_scenarios_pass",
            replay_method="cassette",
            known_limitations=[
                KnownLimitation(
                    code="release_gate_scope",
                    severity="NON_DETERMINISTIC_SIDE_EFFECT",
                    message="Proof applies only to the scenarios in the readiness policy.",
                    subject="release_gate",
                    certificate_blocking=False,
                )
            ],
        )

        signed_dict = generate_certificate(
            incident_id=readiness_check.id,
            root_hash="",
            integrity_status="verified",
            replay_result={
                "scenario_run_id": readiness_check.scenario_run_id,
                "verdict": readiness_check.verdict,
            },
            original_decision="release_gate_check",
            mutated_decision="pass" if readiness_check.verdict == "passed" else "fail",
            fix_config={"policy_id": policy.id, "required_scenarios": policy.required_scenario_ids},
            expected_correct_behavior="all_required_scenarios_pass",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        cert = ProofCertificate(
            id=f"por-{uuid.uuid4().hex[:8]}",
            org_id=readiness_check.org_id,
            certificate_id=signed_dict.get("certificate_id", "por-cert-v1"),
            certificate_type="proof_of_readiness",
            subject_id=readiness_check.id,
            claim=claim,
            issued_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            signature=signed_dict.get("signature", ""),
            signed_payload=signed_dict,
            integrity_status="verified",
            known_limitations=claim.known_limitations,
        )
        self.storage.create_proof_certificate(cert)
        return cert


# ---------------------------------------------------------------------------
# Scenario library service
# ---------------------------------------------------------------------------


class ScenarioLibraryService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def promote_candidate(self, candidate_id: str, org_id: str) -> Scenario:
        candidate = self.storage.get_scenario_candidate(candidate_id)
        if candidate is None or candidate.org_id != org_id:
            raise ValueError("Scenario candidate not found")
        if candidate.state == "blocked":
            raise ValueError("Blocked candidate cannot be promoted")

        existing = [s for s in self.storage.list_scenarios(org_id) if s.source_vr_id == candidate.source_vr_id]
        if existing:
            return existing[0]

        vr = self.storage.get_vr(candidate.source_vr_id)
        if vr is None:
            raise ValueError("Source Verification Record not found")

        # Determine expected outcome from the candidate or label.
        expected_outcome = ""
        if candidate.approved_label_id:
            label = self.storage.get_label(candidate.approved_label_id)
            if label:
                expected_outcome = label.expected_outcome
        if not expected_outcome:
            expected_outcome = vr.expected_outcome

        scenario = Scenario(
            id=f"sc-{uuid.uuid4().hex[:8]}",
            org_id=candidate.org_id,
            environment_id=candidate.environment_id,
            source_vr_id=candidate.source_vr_id,
            source_incident_id=candidate.source_incident_id,
            business_title=candidate.business_title,
            source_system_id=candidate.source_system_id,
            expected_outcome=expected_outcome,
            approved_label_id=candidate.approved_label_id,
            replayability=candidate.replayability,
            replayability_score=candidate.replayability_score,
            required_sandbox_id=candidate.required_sandbox_id,
            evidence_refs=[f"vr:{candidate.source_vr_id}"] + (candidate.source_incident_id and [f"incident:{candidate.source_incident_id}"] or []),
            state="active",
        )
        self.storage.create_scenario(scenario)
        candidate.state = "ready"
        self.storage.update_scenario_candidate(candidate)
        return scenario

    def promote_vr(self, vr_id: str, org_id: str) -> Scenario:
        vr = self.storage.get_vr(vr_id)
        if vr is None or vr.org_id != org_id:
            raise ValueError("Verification Record not found")
        candidates = [c for c in self.storage.list_scenario_candidates(org_id) if c.source_vr_id == vr_id]
        if candidates:
            return self.promote_candidate(candidates[0].id, org_id)

        # Create a candidate on the fly and promote it.
        candidate = ScenarioCandidate(
            id=f"sc-{uuid.uuid4().hex[:6]}",
            org_id=vr.org_id,
            environment_id=vr.environment_id,
            source_vr_id=vr.id,
            source_incident_id=vr.promoted_to_incident,
            business_title=vr.business_function or f"Scenario from {vr.id}",
            source_system_id=vr.source_system_id,
            approved_label_id=vr.current_label_id,
            replayability=vr.replayability.value,
            replayability_score=vr.replayability_score,
            required_sandbox_id=vr.sandbox_readiness.get("system_id", ""),
            state="candidate",
        )
        self.storage.create_scenario_candidate(candidate)
        return self.promote_candidate(candidate.id, org_id)


# ---------------------------------------------------------------------------
# Scenario run service
# ---------------------------------------------------------------------------


class ScenarioRunService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def _run_single_scenario(self, scenario: Scenario, agent_version: str, agent_kwargs: Optional[dict] = None) -> ScenarioRunResult:
        vr = self.storage.get_vr(scenario.source_vr_id)
        if vr is None:
            return ScenarioRunResult(
                scenario_id=scenario.id,
                status="errored",
                expected_decision=scenario.expected_outcome,
                reason="Source Verification Record not found",
            )

        replay_service = ReplayService(self.registry)
        snapshot = replay_service._snapshot_from_vr(vr)

        # Determine scenario id from source.
        scenario_id = "lending-denial"
        for sid in SCENARIOS:
            if sid in scenario.source_system_id or sid in vr.agent_id or sid in scenario.business_title.lower():
                scenario_id = sid
                break

        agent_fn = self.registry.get_agent(scenario_id)
        try:
            result = replay_snapshot(snapshot, agent_fn, agent_kwargs=agent_kwargs)
            actual = result.get("decision") or ""
            status = "passed" if actual == scenario.expected_outcome else "failed"
            return ScenarioRunResult(
                scenario_id=scenario.id,
                status=status,
                expected_decision=scenario.expected_outcome,
                actual_decision=actual,
                reason="" if status == "passed" else f"Expected {scenario.expected_outcome}, got {actual}",
            )
        except Exception as exc:
            return ScenarioRunResult(
                scenario_id=scenario.id,
                status="errored",
                expected_decision=scenario.expected_outcome,
                reason=str(exc),
            )

    def run(self, scenario_ids: list[str], agent_version: str, org_id: str, environment_id: str = "env:demo", fix_config: Optional[dict] = None) -> ScenarioRun:
        if not scenario_ids:
            scenario_ids = [s.id for s in self.storage.list_scenarios(org_id, environment_id) if s.state == "active"]
        if not scenario_ids:
            raise ValueError("No scenarios available to run")

        run = ScenarioRun(
            id=f"sr-{uuid.uuid4().hex[:8]}",
            org_id=org_id,
            environment_id=environment_id,
            agent_version=agent_version,
            scenario_ids=scenario_ids,
            status="running",
        )
        self.storage.create_scenario_run(run)

        results: list[ScenarioRunResult] = []
        for sid in scenario_ids:
            scenario = self.storage.get_scenario(sid)
            if scenario is None or scenario.org_id != org_id:
                results.append(
                    ScenarioRunResult(
                        scenario_id=sid,
                        status="errored",
                        expected_decision="",
                        reason="Scenario not found",
                    )
                )
                continue
            agent_kw = dict(fix_config or {})
            results.append(self._run_single_scenario(scenario, agent_version, agent_kwargs=agent_kw))

        run.results = results
        run.status = "completed"
        run.summary = {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == "passed"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "errored": sum(1 for r in results if r.status == "errored"),
            "escalation_required": sum(1 for r in results if r.status == "escalation_required"),
            "non_deterministic": sum(1 for r in results if r.status == "non_deterministic"),
        }
        self.storage.update_scenario_run(run)

        # Update scenario last_run_status references.
        for r in results:
            scenario = self.storage.get_scenario(r.scenario_id)
            if scenario is not None:
                scenario.last_run_status = r.status
                self.storage.update_scenario(scenario)

        return run


# ---------------------------------------------------------------------------
# Readiness service
# ---------------------------------------------------------------------------


class ReadinessService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def create_policy(
        self,
        org_id: str,
        environment_id: str,
        name: str,
        required_scenario_ids: list[str],
        pass_condition: str = "all_pass",
    ) -> ReadinessPolicy:
        policy = ReadinessPolicy(
            id=f"rp-{uuid.uuid4().hex[:8]}",
            org_id=org_id,
            environment_id=environment_id,
            name=name,
            required_scenario_ids=required_scenario_ids,
            pass_condition=pass_condition,
            enabled=True,
            version=1,
            change_history=[{"action": "created", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}],
        )
        return self.storage.create_readiness_policy(policy)

    def run_check(self, policy_id: str, agent_version: str, org_id: str, environment_id: str = "env:demo", fix_config: Optional[dict] = None) -> ReadinessCheck:
        policy = self.storage.get_readiness_policy(policy_id)
        if policy is None or policy.org_id != org_id:
            raise ValueError("Readiness policy not found")
        if not policy.enabled:
            raise ValueError("Readiness policy is disabled")

        run_service = ScenarioRunService(self.registry)
        scenario_run = run_service.run(policy.required_scenario_ids, agent_version, org_id, environment_id, fix_config=fix_config)

        failing = [r.scenario_id for r in scenario_run.results if r.status == "failed"]
        errored = [r.scenario_id for r in scenario_run.results if r.status == "errored"]
        verdict = "passed" if not failing and not errored else "failed"

        check = ReadinessCheck(
            id=f"rc-{uuid.uuid4().hex[:8]}",
            org_id=org_id,
            environment_id=environment_id,
            policy_id=policy.id,
            agent_version=agent_version,
            scenario_run_id=scenario_run.id,
            verdict=verdict,
            failing_scenarios=failing,
            errored_scenarios=errored,
        )
        self.storage.create_readiness_check(check)

        if verdict == "passed":
            cert = CertificateService(self.registry).issue_proof_of_readiness(check)
            check.certificate_id = cert.id
            self.storage.create_readiness_check(check)

        return check


# ---------------------------------------------------------------------------
# Release gate service
# ---------------------------------------------------------------------------


class ReleaseGateService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def check(
        self,
        policy_id: str,
        agent_version: str,
        org_id: str,
        environment_id: str = "env:demo",
        fix_config: Optional[dict] = None,
    ) -> ReleaseGateResult:
        try:
            readiness = ReadinessService(self.registry)
            check = readiness.run_check(policy_id, agent_version, org_id, environment_id, fix_config=fix_config)
        except Exception:
            result = ReleaseGateResult(
                id=f"rg-{uuid.uuid4().hex[:8]}",
                org_id=org_id,
                readiness_check_id="",
                status="error",
                error_code="readiness_check_failed",
                retry_guidance="Retry the request; if the error persists, verify the policy and scenario configuration.",
            )
            result.ci_cd_command = self._ci_cd_command(policy_id, agent_version)
            self.storage.create_release_gate_result(result)
            return result

        status = "pass" if check.verdict == "passed" else "fail"
        result = ReleaseGateResult(
            id=f"rg-{uuid.uuid4().hex[:8]}",
            org_id=org_id,
            readiness_check_id=check.id,
            status=status,
            failing_scenarios=check.failing_scenarios,
            errored_scenarios=check.errored_scenarios,
            certificate_id=check.certificate_id,
        )
        result.ci_cd_command = self._ci_cd_command(policy_id, agent_version)
        self.storage.create_release_gate_result(result)
        return result

    def _ci_cd_command(self, policy_id: str, agent_version: str) -> str:
        return (
            f"curl -X POST https://api.getnotary.ai/v1/release-gate/checks "
            f'-H "Authorization: Bearer <token>" '
            f'-H "Content-Type: application/json" '
            f'-d \'{{"policy_id": "{policy_id}", "agent_version": "{agent_version}"}}\''
        )


# ---------------------------------------------------------------------------
# Action eligibility service
# ---------------------------------------------------------------------------


class ActionEligibilityService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.storage = registry.storage

    def check(self, vr_id: str, action: str) -> ActionEligibility:
        vr = self.storage.get_vr(vr_id)
        if vr is None:
            return ActionEligibility(action=action, eligible=False, reason="Verification Record not found")

        label = self.storage.get_label(vr.current_label_id) if vr.current_label_id else None
        replay_runs = self.storage.list_replay_runs_for_vr(vr_id)
        latest_replay = replay_runs[-1] if replay_runs else None
        mutations = self.storage.list_mutation_tests_for_vr(vr_id)
        latest_mutation = mutations[-1] if mutations else None

        if action == "replay":
            if vr.replayability == ReplayabilityStatus.evidence_only:
                return ActionEligibility(
                    action=action,
                    eligible=False,
                    reason="Evidence-only record cannot be replayed",
                    next_action="Review evidence manually",
                )
            if vr.replayability == ReplayabilityStatus.missing_context:
                return ActionEligibility(action=action, eligible=False, reason="Missing cassette or context", next_action="Capture API/tool responses")
            if not any(e.kind in (EventKind.api_response, EventKind.tool_call) for e in vr.events):
                return ActionEligibility(action=action, eligible=False, reason="No cassette entries", next_action="Capture API/tool responses")
            return ActionEligibility(action=action, eligible=True, reason="Cassette replay available")

        if action == "mutation":
            if latest_replay is None:
                return ActionEligibility(action=action, eligible=False, reason="Replay not run", next_action="Run replay first")
            if latest_replay.status != "replayed":
                return ActionEligibility(action=action, eligible=False, reason=f"Replay status: {latest_replay.status}", next_action="Resolve replay blockers")
            if not label:
                return ActionEligibility(action=action, eligible=False, reason="Missing expected outcome label", next_action="Add or approve label")
            if label.status != "active":
                return ActionEligibility(action=action, eligible=False, reason="Label not approved", next_action="Approve the label")
            return ActionEligibility(action=action, eligible=True, reason="Ready for fix verification")

        if action == "issue_proof":
            if latest_mutation is None:
                return ActionEligibility(action=action, eligible=False, reason="Mutation test not run", next_action="Run mutation test")
            if latest_mutation.verdict != "verified":
                return ActionEligibility(
                    action=action,
                    eligible=False,
                    reason=f"Mutation not verified: {latest_mutation.verdict}",
                    next_action="Fix the agent and re-run mutation",
                )
            limitations = KnownLimitationService(self.registry).from_vr_and_replay(vr, latest_replay)
            for lim in latest_mutation.known_limitations:
                limitations.append(lim)
            blocking = KnownLimitationService(self.registry).blocking(limitations)
            if blocking:
                return ActionEligibility(
                    action=action,
                    eligible=False,
                    reason=f"Certificate-blocking limitations: {[lim.code for lim in blocking]}",
                    blocking_limitations=blocking,
                    next_action="Resolve certificate-blocking limitations",
                )
            return ActionEligibility(action=action, eligible=True, reason="Ready to issue proof")

        if action == "promote_to_scenario":
            if latest_mutation is None or latest_mutation.verdict != "verified":
                return ActionEligibility(action=action, eligible=False, reason="Verified mutation required", next_action="Run and verify mutation")
            if not label:
                return ActionEligibility(action=action, eligible=False, reason="Approved label required", next_action="Add label")
            return ActionEligibility(action=action, eligible=True, reason="Ready to promote to scenario")

        return ActionEligibility(action=action, eligible=False, reason=f"Unknown action: {action}")
