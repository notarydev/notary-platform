"""Scenario-backed demo catalog for the Notary Platform (WO-80).

Creates 20 Verification Records covering the full product surface:
replayable, missing label, missing cassette, evidence-only, requires sandbox,
determinism flags, and scenario candidates. Also creates incidents, proofs,
and scenario candidates.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from notary_platform.certificates import generate_certificate
from notary_platform.demo_scenarios import SCENARIOS, build_snapshot
from notary_platform.models import (
    AIExecutionEvent,
    DataSourceType,
    EventKind,
    HumanLabel,
    IncidentStatus,
    ReplayabilityStatus,
    ScenarioCandidate,
    SystemConnection,
    VerificationRecord,
)
from notary_platform.platform_data import DEMO_AGENTS, DEMO_SYSTEMS
from notary_platform.replay_engine.mutation import run_mutation
from notary_platform.replay_engine.worker import run_replay


@dataclass
class DemoCase:
    scenario_id: str
    business_title: str
    domain: str
    source_system_id: str
    source_record_ref: str
    agent_id: str
    capture_source: str
    replayability: ReplayabilityStatus
    missing_prerequisites: list[str] = field(default_factory=list)
    non_deterministic_flags: list[dict] = field(default_factory=list)
    expected_outcome: str = ""
    label_state: str = "none"  # none | suggested | approved
    sandbox_readiness: dict = field(default_factory=dict)
    incident_state: str = "none"  # none | ingested | replayed | mitigated | certified
    proof_state: str = "none"  # none | issued
    scenario_state: str = "none"  # none | candidate | ready | blocked
    next_action: str = ""


DEMO_CASES: list[DemoCase] = [
    DemoCase(
        scenario_id="vr-northstar-001",
        business_title="Bereavement refund misrepresentation fixed",
        domain="Airline / Customer Support",
        source_system_id="sys:salesforce-service-cloud",
        source_record_ref="CASE-50093821",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.replayable,
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={
            "required": True, "system_id": "sys:bereavement-policy-api", "ready": True,
            "fix_config": {"require_policy_match_for_refund_claims": True, "escalate_when_policy_requires_human_review": True},
        },
        incident_state="certified",
        proof_state="issued",
        scenario_state="ready",
        next_action="View proof and export certificate",
    ),
    DemoCase(
        scenario_id="northstar-missing-label",
        business_title="Refund misrepresentation missing label",
        domain="Airline / Customer Support",
        source_system_id="sys:salesforce-service-cloud",
        source_record_ref="CASE-50093822",
        agent_id="agent:support-bot-v42",
        capture_source="api_submission",
        replayability=ReplayabilityStatus.requires_human_label,
        missing_prerequisites=["human_label"],
        expected_outcome="",
        label_state="none",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": True},
        incident_state="none",
        next_action="Add or approve expected outcome label",
    ),
    DemoCase(
        scenario_id="northstar-missing-cassette",
        business_title="Refund misrepresentation missing cassette",
        domain="Airline / Customer Support",
        source_system_id="sys:salesforce-service-cloud",
        source_record_ref="CASE-50093823",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.missing_context,
        missing_prerequisites=["cassette_data"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": False},
        incident_state="none",
        next_action="Capture bereavement-policy-api response cassette",
    ),
    DemoCase(
        scenario_id="support-handoff-ignored",
        business_title="Support handoff ignored",
        domain="Customer Support",
        source_system_id="sys:nri-ticketing",
        source_record_ref="TKT-8842",
        agent_id="agent:support-bot-v42",
        capture_source="manual_submission",
        replayability=ReplayabilityStatus.partially_replayable,
        missing_prerequisites=["full_cassette"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": False, "ready": True},
        incident_state="ingested",
        next_action="Add transcript / chat cassette for full replay",
    ),
    DemoCase(
        scenario_id="support-escalation-webhook",
        business_title="Support escalation webhook",
        domain="Customer Support",
        source_system_id="sys:nri-ticketing",
        source_record_ref="TKT-9912",
        agent_id="agent:support-bot-v42",
        capture_source="webhook",
        replayability=ReplayabilityStatus.requires_human_label,
        missing_prerequisites=["human_label"],
        expected_outcome="",
        label_state="suggested",
        sandbox_readiness={"required": False, "ready": True},
        incident_state="none",
        next_action="Review suggested label and approve",
    ),
    DemoCase(
        scenario_id="prior-auth-denial",
        business_title="Prior authorization denial",
        domain="Healthcare / Insurance",
        source_system_id="sys:bereavement-policy-api",
        source_record_ref="PA-M-4481",
        agent_id="agent:support-bot-v43",
        capture_source="api_submission",
        replayability=ReplayabilityStatus.requires_sandbox,
        missing_prerequisites=["sandbox"],
        expected_outcome="ESCALATE_TO_HUMAN_REVIEW",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": False},
        incident_state="none",
        next_action="Configure policy API sandbox",
    ),
    DemoCase(
        scenario_id="prior-auth-timeout",
        business_title="Prior authorization timeout",
        domain="Healthcare / Insurance",
        source_system_id="sys:bereavement-policy-api",
        source_record_ref="PA-M-5512",
        agent_id="agent:support-bot-v43",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.partially_replayable,
        missing_prerequisites=["stable_tool_api"],
        expected_outcome="ESCALATE_TO_HUMAN_REVIEW",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": True},
        incident_state="replayed",
        next_action="Verify fix handles timeout gracefully",
    ),
    DemoCase(
        scenario_id="hiring-screen-rejection",
        business_title="Hiring screen rejection",
        domain="Hiring / HR Compliance",
        source_system_id="sys:bereavement-policy-api",
        source_record_ref="C-9021",
        agent_id="agent:support-bot-dev",
        capture_source="manual_submission",
        replayability=ReplayabilityStatus.evidence_only,
        missing_prerequisites=["deterministic_model"],
        expected_outcome="ADVANCE_TO_REVIEW",
        label_state="approved",
        sandbox_readiness={"required": False, "ready": False},
        incident_state="none",
        next_action="Evidence-only review; remove age-proxy feature",
    ),
    DemoCase(
        scenario_id="refund-denial-policy-breach",
        business_title="Refund denial policy breach",
        domain="Payments / Support",
        source_system_id="sys:payment-gateway",
        source_record_ref="REF-7712",
        agent_id="agent:support-bot-v42",
        capture_source="webhook",
        replayability=ReplayabilityStatus.replayable,
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:payment-gateway", "ready": True},
        incident_state="mitigated",
        next_action="Issue proof for verified policy fix",
    ),
    DemoCase(
        scenario_id="chargeback-mishandled",
        business_title="Chargeback mishandled",
        domain="Payments",
        source_system_id="sys:payment-gateway",
        source_record_ref="CB-3321",
        agent_id="agent:support-bot-v42",
        capture_source="source_system_adapter",
        replayability=ReplayabilityStatus.missing_context,
        missing_prerequisites=["source_system_connector", "cassette_data"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:payment-gateway", "ready": False},
        incident_state="none",
        next_action="Build payment-source connector",
    ),
    DemoCase(
        scenario_id="booking-refund-missing-db",
        business_title="Booking refund missing DB state",
        domain="Airline / Passenger Services",
        source_system_id="sys:passenger-booking",
        source_record_ref="BK-11029",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.partially_replayable,
        missing_prerequisites=["db_snapshot"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:passenger-booking", "ready": False},
        incident_state="replayed",
        next_action="Provide booking DB snapshot for full replay",
    ),
    DemoCase(
        scenario_id="retrieval-mismatch",
        business_title="Retrieval mismatch",
        domain="Knowledge / RAG",
        source_system_id="sys:knowledge-base",
        source_record_ref="DOC-4412",
        agent_id="agent:support-bot-v42",
        capture_source="trace_import",
        replayability=ReplayabilityStatus.partially_replayable,
        missing_prerequisites=["retrieval_snapshot"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:knowledge-base", "ready": True},
        incident_state="none",
        next_action="Capture knowledge-base retrieval snapshot",
    ),
    DemoCase(
        scenario_id="hallucinated-citation",
        business_title="Hallucinated citation",
        domain="Knowledge / RAG",
        source_system_id="sys:knowledge-base",
        source_record_ref="DOC-9981",
        agent_id="agent:support-bot-v42",
        capture_source="manual_submission",
        replayability=ReplayabilityStatus.evidence_only,
        missing_prerequisites=["deterministic_model"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="suggested",
        sandbox_readiness={"required": False, "ready": False},
        incident_state="none",
        next_action="Review label; proof will show limitation",
    ),
    DemoCase(
        scenario_id="model-drift",
        business_title="Model drift case",
        domain="Model Provider",
        source_system_id="sys:azure-openai",
        source_record_ref="RUN-2234",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.partially_replayable,
        missing_prerequisites=["model_version_match"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:azure-openai", "ready": True},
        incident_state="replayed",
        next_action="Disclose model drift in proof limitations",
    ),
    DemoCase(
        scenario_id="random-uuid",
        business_title="Random UUID dependency",
        domain="Internal Service",
        source_system_id="sys:salesforce-service-cloud",
        source_record_ref="CASE-50093999",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.partially_replayable,
        missing_prerequisites=["rng_seed"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": True},
        incident_state="replayed",
        next_action="Seal RNG seed or use deterministic IDs",
    ),
    DemoCase(
        scenario_id="timestamp-dependency",
        business_title="Timestamp dependency",
        domain="Internal Service",
        source_system_id="sys:salesforce-service-cloud",
        source_record_ref="CASE-50094000",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.replayable,
        missing_prerequisites=[],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": True},
        incident_state="replayed",
        next_action="Timestamp sealed; run preflight",
    ),
    DemoCase(
        scenario_id="api-timeout-fixed",
        business_title="API timeout fixed",
        domain="Tool / API",
        source_system_id="sys:payment-gateway",
        source_record_ref="API-T-1123",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.replayable,
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:payment-gateway", "ready": True},
        incident_state="certified",
        proof_state="issued",
        scenario_state="candidate",
        next_action="Promote to scenario",
    ),
    DemoCase(
        scenario_id="webhook-complaint",
        business_title="Webhook complaint",
        domain="Customer Support",
        source_system_id="sys:nri-ticketing",
        source_record_ref="TKT-2231",
        agent_id="agent:support-bot-v42",
        capture_source="webhook",
        replayability=ReplayabilityStatus.requires_human_label,
        missing_prerequisites=["human_label"],
        expected_outcome="",
        label_state="none",
        sandbox_readiness={"required": False, "ready": True},
        incident_state="none",
        next_action="Add Human Label for manual review",
    ),
    DemoCase(
        scenario_id="scenario-candidate-ready",
        business_title="Scenario candidate ready",
        domain="General",
        source_system_id="sys:salesforce-service-cloud",
        source_record_ref="CASE-50094001",
        agent_id="agent:support-bot-v42",
        capture_source="sdk_snapshot",
        replayability=ReplayabilityStatus.replayable,
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": True},
        incident_state="mitigated",
        scenario_state="candidate",
        next_action="Issue proof then promote to scenario",
    ),
    DemoCase(
        scenario_id="release-gate-blocked",
        business_title="Release gate blocked",
        domain="CI/CD",
        source_system_id="sys:github-actions",
        source_record_ref="REL-001",
        agent_id="agent:support-bot-v42",
        capture_source="eval_adapter",
        replayability=ReplayabilityStatus.replayable,
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="approved",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": True},
        incident_state="mitigated",
        scenario_state="blocked",
        next_action="Fix scenario run and re-run release gate",
    ),
    DemoCase(
        scenario_id="northstar-webhook",
        business_title="Northstar refund webhook",
        domain="Airline / Customer Support",
        source_system_id="sys:salesforce-service-cloud",
        source_record_ref="CASE-50094002",
        agent_id="agent:support-bot-v42",
        capture_source="webhook",
        replayability=ReplayabilityStatus.requires_human_label,
        missing_prerequisites=["human_label"],
        expected_outcome="ESCALATE_TO_HUMAN",
        label_state="suggested",
        sandbox_readiness={"required": True, "system_id": "sys:bereavement-policy-api", "ready": True},
        incident_state="none",
        next_action="Review suggested label",
    ),
]


def _agent_for_case(case: DemoCase) -> Any:
    for a in DEMO_AGENTS:
        if a.id == case.agent_id:
            return a
    return DEMO_AGENTS[0]


def _system_for_case(case: DemoCase) -> SystemConnection | None:
    for s in DEMO_SYSTEMS:
        if s.id == case.source_system_id:
            return s
    return None


def _base_events_for_case(case: DemoCase) -> list[AIExecutionEvent]:
    events: list[AIExecutionEvent] = []
    order = 0

    # Input / source record reference
    events.append(
        AIExecutionEvent(
            id=uuid.uuid4().hex,
            kind=EventKind.human_action,
            payload={"source_record_ref": case.source_record_ref, "domain": case.domain},
            source_system=case.source_system_id,
            order=order,
        )
    )
    order += 1

    # Model call if applicable
    if case.capture_source in {"sdk_snapshot", "api_submission", "webhook"}:
        events.append(
            AIExecutionEvent(
                id=uuid.uuid4().hex,
                kind=EventKind.model_call,
                payload={"model": "demo-model", "policy_version": "v1", "temperature": 0.0, "seed": 12345},
                source_system="sys:model-provider",
                order=order,
            )
        )
        order += 1

    # Tool / cassette call (unless missing cassette is the blocker)
    sys = _system_for_case(case)
    if sys and sys.type in {"tool_api", "source_system"} and "cassette_data" not in case.missing_prerequisites:
        resp: dict[str, Any] = {"status": "ok"}
        if case.scenario_id.startswith("prior-auth"):
            resp = {"risk_score": "high", "physician_note": "continued skilled care required"}
        elif case.scenario_id.startswith(("vr-northstar", "northstar")):
            resp = {"retroactive_refund_allowed": False, "human_review_required": True, "policy_version": "bereavement-policy-v7"}
        elif case.scenario_id.startswith("api-timeout"):
            resp = {"status": "ok", "latency_ms": 120}
        elif case.scenario_id.startswith("refund"):
            resp = {"refund_eligible": True}
        elif case.scenario_id.startswith("retrieval"):
            resp = {"documents": ["doc-1", "doc-2"]}
        events.append(
            AIExecutionEvent(
                id=uuid.uuid4().hex,
                kind=EventKind.tool_call,
                payload={"endpoint": f"POST {sys.id}", "response": resp},
                source_system=sys.id,
                order=order,
            )
        )
        order += 1

    # Decision
    decisions = {
        "vr-northstar-001": "OFFER_RETROACTIVE_REFUND",
        "prior-auth-denial": "DENY",
        "support-handoff-ignored": "CONTINUE_BOT",
        "hiring-screen-rejection": "REJECT",
        "refund-denial-policy-breach": "DENY_REFUND",
        "api-timeout-fixed": "TIMEOUT",
    }
    events.append(
        AIExecutionEvent(
            id=uuid.uuid4().hex,
            kind=EventKind.decision,
            payload={"decision": decisions.get(case.scenario_id, "REVIEW")},
            source_system=case.source_system_id,
            order=order,
        )
    )
    order += 1

    # Non-deterministic flags as events
    if "rng_seed" in case.missing_prerequisites:
        events.append(
            AIExecutionEvent(
                id=uuid.uuid4().hex,
                kind=EventKind.rng_seed,
                payload={"seed": "not_sealed"},
                source_system=case.source_system_id,
                order=order,
            )
        )
        order += 1
    if "timestamp" in case.missing_prerequisites or case.scenario_id == "timestamp-dependency":
        events.append(
            AIExecutionEvent(
                id=uuid.uuid4().hex,
                kind=EventKind.timestamp,
                payload={"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sealed": case.scenario_id == "timestamp-dependency"},
                source_system=case.source_system_id,
                order=order,
            )
        )

    return events


def _snapshot_for_case(case: DemoCase) -> dict[str, Any] | None:
    if case.capture_source != "sdk_snapshot":
        return None
    base = SCENARIOS.get("vr-northstar-001") or list(SCENARIOS.values())[0]
    return build_snapshot(base)


def _run_full_proof_loop(incident: Any, snapshot: dict[str, Any], agent_fn: Callable[..., Any]) -> None:
    run_replay(incident, snapshot, agent_fn)
    result = run_mutation(
        snapshot, agent_fn,
        {"require_policy_match_for_refund_claims": True, "escalate_when_policy_requires_human_review": True},
        expected_correct_behavior="ESCALATE_TO_HUMAN",
    )
    incident.mutation_result = result
    if result.get("mitigated"):
        incident.status = IncidentStatus.mitigated
    cert = generate_certificate(
        incident_id=incident.incident_id,
        root_hash=incident.snapshot_summary.get("root_hash", ""),
        integrity_status="verified",
        replay_result=incident.replay_result,
        original_decision=result.get("original_decision"),
        mutated_decision=result.get("mutated_decision"),
        fix_config=result.get("fix_config", {}),
        expected_correct_behavior="ESCALATE_TO_HUMAN",
        timestamp=incident.snapshot_summary.get("timestamp", ""),
    )
    incident.certificate = cert
    incident.status = IncidentStatus.certified


def build_catalog(registry: Any, org_id: str) -> dict[str, Any]:
    """Seed the full demo catalog using product services and return counts."""
    from notary_platform.api_server.routers.verification import _assess_replayability
    from notary_platform.services import (
        CertificateService,
        IngestionService,
        MutationService,
        ReplayService,
        ScenarioLibraryService,
    )

    storage = registry.storage
    ingestion = IngestionService(registry)
    replay_service = ReplayService(registry)
    mutation_service = MutationService(registry)
    certificate_service = CertificateService(registry)
    scenario_library = ScenarioLibraryService(registry)

    created_vrs: list[VerificationRecord] = []
    created_incidents: list[Any] = []
    created_labels: list[HumanLabel] = []
    created_candidates: list[ScenarioCandidate] = []
    created_proofs = 0

    for case in DEMO_CASES:
        try:
            source_type = DataSourceType(case.capture_source)
        except ValueError:
            source_type = DataSourceType.api_submission

        vr = VerificationRecord(
            id=ingestion._next_vr_id(),
            org_id=org_id,
            environment_id="env:demo",
            source_type=source_type,
            source_system_id=case.source_system_id,
            source_record_ref=case.source_record_ref,
            agent_id=case.agent_id,
            agent_version="1.2.0",
            model_provider="Demo Model Provider",
            model_name="demo-model",
            policy_version="v1",
            expected_outcome=case.expected_outcome,
            business_function=f"Demo {case.domain}: {case.business_title}",
            is_demo=True,
            events=_base_events_for_case(case),
            sandbox_readiness=case.sandbox_readiness,
            next_action=case.next_action,
        )
        vr.computed_replayability, vr.replayability_reason, vr.missing_prerequisites = _assess_replayability(vr)
        # Store computed replayability before we override for demo
        vr.replayability = vr.computed_replayability
        # Force the intended replayability state for product demo purposes.
        if vr.computed_replayability != case.replayability:
            vr.demo_replayability = case.replayability
            vr.demo_replayability_reason = "Demo-seeded: overrides computed state for storytelling"
            vr.replayability = case.replayability
            vr.replayability_source = "demo_seed"
        if case.replayability == ReplayabilityStatus.requires_human_label:
            vr.replayability_reason = "Cassette data is present but no expected outcome label has been added."
            vr.missing_prerequisites = ["human_label"]
        elif case.replayability == ReplayabilityStatus.requires_sandbox:
            vr.replayability_reason = "Sandbox environment required for replay."
            vr.missing_prerequisites = ["sandbox"]
        elif case.replayability == ReplayabilityStatus.missing_context:
            vr.replayability_reason = "Missing cassette or source-system context."
        elif case.replayability == ReplayabilityStatus.evidence_only:
            vr.replayability_reason = "Non-deterministic model output; evidence-only review."
        elif case.replayability == ReplayabilityStatus.partially_replayable:
            vr.replayability_reason = "Partial replay: some context missing or non-deterministic."

        # Apply deterministic flags based on case story.
        if "rng_seed" in case.missing_prerequisites:
            vr.non_deterministic_flags.append({
                "component": "rng_seed",
                "severity": "NON_DETERMINISTIC_SIDE_EFFECT",
                "description": "Random UUID dependency not sealed.",
                "remediation": "Capture deterministic seed.",
            })
        if "timestamp" in case.missing_prerequisites or case.scenario_id == "timestamp-dependency":
            severity = "NON_DETERMINISTIC_SIDE_EFFECT" if case.scenario_id == "timestamp-dependency" else "NON_DETERMINISTIC_CORE"
            description = "Timestamp sealed for deterministic replay." if case.scenario_id == "timestamp-dependency" else "Timestamp dependency detected."
            vr.non_deterministic_flags.append({
                "component": "timestamp",
                "severity": severity,
                "description": description,
                "remediation": "Seal timestamp or use fixed test time.",
            })
        if "model_version_match" in case.missing_prerequisites:
            vr.non_deterministic_flags.append({
                "component": "model_drift",
                "severity": "NON_DETERMINISTIC_SIDE_EFFECT",
                "description": "Current model may differ from recorded behavior.",
                "remediation": "Pin model version and disclose drift.",
            })
        if "deterministic_model" in case.missing_prerequisites:
            vr.non_deterministic_flags.append({
                "component": "llm_call",
                "severity": "NON_DETERMINISTIC_CORE",
                "description": "LLM outputs are non-deterministic.",
                "remediation": "Use temp=0 or treat as evidence-only.",
            })
        if "db_snapshot" in case.missing_prerequisites:
            vr.non_deterministic_flags.append({
                "component": "missing_cassette",
                "severity": "NON_DETERMINISTIC_CORE",
                "description": "Claims DB state not captured.",
                "remediation": "Provide DB snapshot for full replay.",
            })
        if "retrieval_snapshot" in case.missing_prerequisites:
            vr.non_deterministic_flags.append({
                "component": "missing_cassette",
                "severity": "NON_DETERMINISTIC_SIDE_EFFECT",
                "description": "Knowledge-base retrieval not snapshotted.",
                "remediation": "Capture retrieval context.",
            })

        storage.create_vr(vr)
        created_vrs.append(vr)

        # Labels
        if case.label_state in {"suggested", "approved"} and case.expected_outcome:
            label = HumanLabel(
                id=uuid.uuid4().hex,
                verification_record_id=vr.id,
                expected_outcome=case.expected_outcome,
                reviewer="Demo QA Lead" if case.label_state == "approved" else "",
                role="QA",
                reason=f"{case.label_state.capitalize()} label for {case.business_title}",
                category="incident_type",
                suggested_confidence=0.75 if case.label_state == "suggested" else 1.0,
                suggested_by="heuristic" if case.label_state == "suggested" else "human",
            )
            if case.label_state == "approved":
                label.approval_reason = "Approved for demo"
            if case.label_state == "suggested":
                label.status = "suggested"
            storage.create_label(label)
            vr.current_label_id = label.id
            vr.label_source = label.suggested_by
            # Re-assess replayability now that label state is set.
            vr.replayability, vr.replayability_reason, vr.missing_prerequisites = _assess_replayability(vr)
            vr.replayability = case.replayability
            storage.update_vr(vr)
            created_labels.append(label)

        # Incident + proof loop via product services.
        incident: Any | None = None
        if case.incident_state != "none":
            incident = ingestion.create_incident_from_vr(vr)
            created_incidents.append(incident)

            if case.incident_state in {"replayed", "mitigated", "certified"}:
                replay_service.run_replay(vr.id, org_id)

            if case.incident_state in {"mitigated", "certified"}:
                fix_config = case.sandbox_readiness.get("fix_config", {"threshold": 620}) if isinstance(case.sandbox_readiness, dict) else {"threshold": 620}
                mutation_service.run_mutation(vr.id, org_id, fix_config, expected_correct_behavior=case.expected_outcome or "APPROVE")

            if case.proof_state == "issued" or case.incident_state == "certified":
                try:
                    certificate_service.issue_proof_of_mitigation(vr.id, org_id)
                    created_proofs += 1
                except ValueError:
                    # Some demo cases do not have a matching scenario agent; skip proof for those.
                    if incident is not None:
                        incident._record_custody(
                            "proof_skipped",
                            actor="demo_catalog",
                            detail="Mutation did not verify against available scenario agent",
                        )
                        storage.update_incident(incident)

        # Scenario candidate
        if case.scenario_state != "none":
            candidate = ScenarioCandidate(
                id=f"sc-{uuid.uuid4().hex[:6]}",
                org_id=org_id,
                environment_id="env:demo",
                source_vr_id=vr.id,
                source_incident_id=incident.incident_id if incident else "",
                business_title=case.business_title,
                source_system_id=case.source_system_id,
                approved_label_id=vr.current_label_id,
                replayability=case.replayability.value,
                replayability_score=vr.replayability_score,
                required_sandbox_id=case.sandbox_readiness.get("system_id", "") if isinstance(case.sandbox_readiness, dict) else "",
                last_run_status=(
                    "passed" if case.scenario_state == "ready" else "not_started" if case.scenario_state == "candidate" else "failed"
                ),
                release_gate_ids=["gate:high-risk-support-policy"]
                if case.scenario_id in {"vr-northstar-001", "api-timeout-fixed", "release-gate-blocked"}
                else [],
                next_action=(
                    "Promote to scenario library"
                    if case.scenario_state == "candidate"
                    else "Review release gate failure" if case.scenario_state == "blocked" else "In scenario library"
                ),
                state=case.scenario_state,
            )
            storage.create_scenario_candidate(candidate)
            created_candidates.append(candidate)

            # Promote ready scenarios into the Scenario Library.
            if case.scenario_state == "ready":
                scenario_library.promote_candidate(candidate.id, org_id)

    # Link systems to created VRs/incidents/proofs/scenarios.
    for sys in DEMO_SYSTEMS:
        sys.linked_vrs = [
            vr.id for vr in created_vrs
            if vr.source_system_id == sys.id or sys.id in {e.source_system for e in vr.events}
        ]
        sys.linked_incidents = [
            inc.incident_id for inc in created_incidents
            if any(
                vr.promoted_to_incident == inc.incident_id
                and (vr.source_system_id == sys.id or sys.id in {e.source_system for e in vr.events})
                for vr in created_vrs
            )
        ]
        sys.linked_proofs = [
            inc.incident_id for inc in created_incidents
            if inc.certificate and inc.incident_id in sys.linked_incidents
        ]
        scenarios = storage.list_scenarios(org_id)
        sys.linked_scenarios = [sc.id for sc in scenarios if sc.source_system_id == sys.id]

    return {
        "created_verification_records": len(created_vrs),
        "created_incidents": len(created_incidents),
        "created_replay_runs": len(storage.list_replay_runs_for_vr("")),
        "created_mutation_tests": len(storage.list_mutation_tests_for_vr("")),
        "created_proof_certificates": len(storage._proof_certs),
        "created_labels": len(created_labels),
        "scenario_candidates": len(created_candidates),
        "scenarios": len(storage.list_scenarios(org_id)),
        "systems": len(DEMO_SYSTEMS),
        "known_blockers": [],
    }


def seed_northstar_release_gate_demo(registry: Any, org_id: str) -> dict[str, Any]:
    """Create the deterministic Northstar Air flagship Release Gate demo path."""
    from notary_platform.services import (
        CertificateService,
        IngestionService,
        LabelProvenanceService,
        MutationService,
        ReadinessService,
        ReleaseGateService,
        ReplayService,
        ScenarioLibraryService,
    )

    scenario = SCENARIOS["vr-northstar-001"]
    snapshot = build_snapshot(scenario)
    ingestion = IngestionService(registry)
    labels = LabelProvenanceService(registry)
    replay = ReplayService(registry)
    mutation = MutationService(registry)
    certificates = CertificateService(registry)
    scenarios = ScenarioLibraryService(registry)
    readiness = ReadinessService(registry)
    release_gate = ReleaseGateService(registry)

    vr = ingestion.create_from_sdk_snapshot(
        snapshot,
        org_id=org_id,
        agent_id="agent:support-bot-v42",
        environment_id="env:demo",
    )
    vr.business_function = "Northstar Air bereavement refund policy misrepresentation support-bot workflow"
    vr.source_system_id = "sys:salesforce-service-cloud"
    vr.source_record_ref = "50093821"
    vr.external_ref = "CASE-50093821"
    vr.agent_version = scenario.model_version
    vr.model_provider = "Azure OpenAI"
    vr.model_name = scenario.model_name
    vr.policy_version = scenario.policy_version
    vr.expected_outcome = scenario.expected_correct_behavior
    vr.is_demo = True
    vr.sandbox_readiness = {
        "required": True,
        "system_id": "sys:bereavement-policy-api",
        "ready": True,
        "cassette": "sealed",
        "fix_config": scenario.fix_config,
    }
    vr.next_action = "Replay original refund offer, verify escalate-to-human fix, and run Release Gate"
    registry.storage.update_vr(vr)

    label = labels.create_label(
        vr.id,
        org_id,
        expected_outcome=scenario.expected_correct_behavior,
        reviewer="Northstar Legal Review",
        role="Consumer Compliance",
        reason=(
            "Customer asked about bereavement refund. Policy requires escalation to human"
            " but bot offered a retroactive refund anyway."
        ),
    )
    incident = ingestion.create_incident_from_vr(vr)
    replay_run = replay.run_replay(vr.id, org_id)
    mutation_test = mutation.run_mutation(
        vr.id,
        org_id,
        scenario.fix_config,
        expected_correct_behavior=scenario.expected_correct_behavior,
    )
    mitigation_proof = certificates.issue_proof_of_mitigation(vr.id, org_id)
    promoted_scenario = scenarios.promote_vr(vr.id, org_id)
    promoted_scenario.business_title = scenario.title
    registry.storage.update_scenario(promoted_scenario)
    policy = readiness.create_policy(
        org_id,
        "env:demo",
        "High-risk support policy gate",
        [promoted_scenario.id],
    )
    gate_before_fix = release_gate.check(
        policy.id,
        agent_version="support-bot-v42",
        org_id=org_id,
        environment_id="env:demo",
    )
    readiness_after_fix = readiness.run_check(
        policy.id,
        agent_version="support-bot-v43",
        org_id=org_id,
        environment_id="env:demo",
        fix_config=scenario.fix_config,
    )
    gate_after_fix = release_gate.check(
        policy.id,
        agent_version="support-bot-v43",
        org_id=org_id,
        environment_id="env:demo",
        fix_config=scenario.fix_config,
    )

    return {
        "demo_org": "Northstar Air",
        "scenario_contract": {
            "scenario_id": scenario.scenario_id,
            "title": scenario.title,
            "seed": scenario.seed,
            "original_captured_decision": scenario.original_decision,
            "expected_correct_behavior": scenario.expected_correct_behavior,
            "failure": (
                "The support bot offered a retroactive bereavement refund despite the policy"
                " API response indicating retroactive refunds are not allowed and human review"
                " is required."
            ),
            "scope": (
                "This proof is scoped to the sealed Northstar Air bereavement-policy cassette and"
                " does not certify general AI safety, transparent capture, or active GRC integrations."
            ),
        },
        "verification_record_id": vr.id,
        "label_id": label.id,
        "incident_id": incident.incident_id,
        "replay_run_id": replay_run.id,
        "mutation_test_id": mutation_test.id,
        "proof_of_mitigation_certificate_id": mitigation_proof.id,
        "scenario_id": promoted_scenario.id,
        "readiness_policy_id": policy.id,
        "readiness_after_fix_id": readiness_after_fix.id,
        "proof_of_readiness_certificate_id": readiness_after_fix.certificate_id,
        "release_gate_before_fix_id": gate_before_fix.id,
        "release_gate_before_fix_status": gate_before_fix.status,
        "release_gate_after_fix_id": gate_after_fix.id,
        "release_gate_after_fix_status": gate_after_fix.status,
        "release_gate_after_fix_certificate_id": gate_after_fix.certificate_id,
        "arc": [
            "original captured decision",
            "replay exact recorded condition",
            "apply fix",
            "verify corrected outcome under same cassette",
            "issue scoped proof",
            "promote to scenario",
            "run readiness",
            "Release Gate fail before fix and pass after fix",
        ],
    }


# Legacy alias for backward compatibility
seed_harborline_release_gate_demo = seed_northstar_release_gate_demo


def build_catalog_legacy(
    storage: Any,
    vr_store: dict[str, VerificationRecord],
    label_store: dict[str, HumanLabel],
    scenario_store: dict[str, ScenarioCandidate],
    org_id: str,
) -> dict[str, Any]:
    """Legacy signature kept for compatibility. Use build_catalog(registry, org_id) for new code."""
    from notary_platform.services import ServiceRegistry

    registry = ServiceRegistry(storage)
    result = build_catalog(registry, org_id)
    # Sync created objects back to legacy dicts for callers that still use them.
    for vr in registry.storage.list_vrs(org_id):
        vr_store[vr.id] = vr
    return result
